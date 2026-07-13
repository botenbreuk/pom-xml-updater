"""
Controller for git status (branch + commits-behind), background fetch / pull,
and the ``.sdkmanrc`` / ``.java-version`` JDK hint.  Exposed to QML as the
``Git`` property.
"""
from __future__ import annotations

import os
import re
import subprocess

from PyQt6.QtCore import (
    QObject, QThread, pyqtProperty, pyqtSignal, pyqtSlot,
)

from core.git_info import get_git_info, is_git_available


def _java_major(value: str) -> int | None:
    """Extract the Java major from strings like '21.0.1-tem', '1.8.0_392',
    'temurin-17', or 'openjdk64-11.0.2' (the last version-ish token wins)."""
    matches = re.findall(r"(?<![\d.])(?:1\.)?(\d{1,2})(?:[._]\d+)*", value)
    return int(matches[-1]) if matches else None


class _GitFetchWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, directory: str) -> None:
        super().__init__()
        self._directory = directory

    def run(self) -> None:
        try:
            subprocess.run(["git", "-C", self._directory, "fetch"],
                           capture_output=True, timeout=15)
        except Exception:
            pass
        self.finished.emit()


class _GitPullWorker(QObject):
    finished = pyqtSignal(bool, str)   # success, error_message

    def __init__(self, directory: str) -> None:
        super().__init__()
        self._directory = directory

    def run(self) -> None:
        try:
            r = subprocess.run(["git", "-C", self._directory, "pull"],
                               capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                self.finished.emit(True, "")
            else:
                self.finished.emit(False, (r.stderr or r.stdout).strip())
        except Exception as exc:
            self.finished.emit(False, str(exc))


class GitController(QObject):
    changed = pyqtSignal()
    javaHintChanged = pyqtSignal()
    pullFailed = pyqtSignal(str)
    reloadRequested = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._available = is_git_available()
        self._dir = ""
        self._branch = ""
        self._behind = 0
        self._has_repo = False
        self._fetching = False
        self._pulling = False
        self._java_version = ""
        self._java_hint_text = ""
        self._java_hint_warn = False
        self._fetch_pairs: set = set()
        self._pull_pairs: set = set()

    # ── properties ────────────────────────────────────────────────────────────

    @pyqtProperty(bool, notify=changed)
    def hasRepo(self) -> bool:
        return self._has_repo

    @pyqtProperty(str, notify=changed)
    def branch(self) -> str:
        return self._branch

    @pyqtProperty(int, notify=changed)
    def behind(self) -> int:
        return self._behind

    @pyqtProperty(bool, notify=changed)
    def fetching(self) -> bool:
        return self._fetching

    @pyqtProperty(bool, notify=changed)
    def pulling(self) -> bool:
        return self._pulling

    @pyqtProperty(str, notify=javaHintChanged)
    def javaHintText(self) -> str:
        return self._java_hint_text

    @pyqtProperty(bool, notify=javaHintChanged)
    def javaHintWarn(self) -> bool:
        return self._java_hint_warn

    # ── slots ─────────────────────────────────────────────────────────────────

    @pyqtSlot(str)
    def setProject(self, directory: str) -> None:
        self._dir = directory
        self._update_java_hint()
        if not directory or not self._available:
            self._has_repo = False
            self._branch = ""
            self._behind = 0
            self._fetching = False
            self.changed.emit()
            return
        info = get_git_info(directory)
        if info is None:
            self._has_repo = False
            self._fetching = False
            self.changed.emit()
            return
        self._has_repo = True
        self._branch = info.branch
        self._behind = info.behind
        self._fetching = True
        self.changed.emit()
        self._start_fetch(directory)

    @pyqtSlot(str)
    def setJavaVersion(self, version: str) -> None:
        self._java_version = version
        self._update_java_hint()

    @pyqtSlot()
    def pull(self) -> None:
        if not self._dir:
            return
        self._pulling = True
        self.changed.emit()
        self._start_pull(self._dir)

    @pyqtSlot()
    def shutdown(self) -> None:
        for thread, _ in list(self._fetch_pairs) + list(self._pull_pairs):
            try:
                if thread.isRunning():
                    thread.quit()
                    thread.wait(2000)
            except RuntimeError:
                pass

    # ── background work ─────────────────────────────────────────────────────────

    def _start_fetch(self, directory: str) -> None:
        worker = _GitFetchWorker(directory)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        worker.finished.connect(lambda d=directory: self._on_fetch_done(d))
        pair = (thread, worker)
        self._fetch_pairs.add(pair)
        thread.finished.connect(lambda _=None, p=pair: self._fetch_pairs.discard(p))
        thread.start()

    def _on_fetch_done(self, directory: str) -> None:
        if directory != self._dir:
            return
        info = get_git_info(directory)
        if info is not None:
            self._has_repo = True
            self._branch = info.branch
            self._behind = info.behind
        self._fetching = False
        self.changed.emit()

    def _start_pull(self, directory: str) -> None:
        worker = _GitPullWorker(directory)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        worker.finished.connect(lambda ok, msg, d=directory: self._on_pull_done(ok, msg, d))
        pair = (thread, worker)
        self._pull_pairs.add(pair)
        thread.finished.connect(lambda _=None, p=pair: self._pull_pairs.discard(p))
        thread.start()

    def _on_pull_done(self, success: bool, message: str, directory: str) -> None:
        self._pulling = False
        if success:
            info = get_git_info(directory)
            if info is not None:
                self._branch = info.branch
                self._behind = info.behind
            self.changed.emit()
            if directory == self._dir:
                self.reloadRequested.emit()
        else:
            self.changed.emit()
            self.pullFailed.emit(message)

    # ── JDK hint (.sdkmanrc / .java-version) ─────────────────────────────────

    def _read_hint(self) -> tuple[str, str] | None:
        """Return (source_file, declared_version) for the project, if any."""
        sdkmanrc = os.path.join(self._dir, ".sdkmanrc")
        if os.path.isfile(sdkmanrc):
            try:
                with open(sdkmanrc) as fh:
                    for line in fh:
                        key, _, value = line.strip().partition("=")
                        if key.strip() == "java" and value.strip():
                            return ".sdkmanrc", value.strip()
            except Exception:
                pass
        java_version = os.path.join(self._dir, ".java-version")
        if os.path.isfile(java_version):
            try:
                with open(java_version) as fh:
                    value = fh.read().strip()
                if value:
                    return ".java-version", value
            except Exception:
                pass
        return None

    def _update_java_hint(self) -> None:
        text, warn = "", False
        hint = self._read_hint() if self._dir else None
        if hint is not None:
            source, declared = hint
            text = f"{source}: java {declared}"
            if self._java_version:
                running = _java_major(self._java_version)
                wanted = _java_major(declared)
                warn = (running is not None and wanted is not None
                        and running != wanted)
        if (text, warn) != (self._java_hint_text, self._java_hint_warn):
            self._java_hint_text = text
            self._java_hint_warn = warn
            self.javaHintChanged.emit()
