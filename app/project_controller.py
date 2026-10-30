"""
Controller for the currently-open project: opening / closing a pom.xml,
the recent-files list, the dependency table model, live Maven Central fetches,
and single-row updates.  Exposed to QML as the ``Project`` context property.
"""
from __future__ import annotations

import os

from PyQt6.QtCore import (
    QObject, QThread, QUrl, pyqtProperty, pyqtSignal, pyqtSlot,
)

from core.version_cache import VersionCache
from core.pom_xml import load as load_pom, save as save_pom
from core.m2_repo import artifact_in_local_repo, artifact_pom_name
from models.dependency import DependencyInfo
from models.settings import AppSettings
from workers.fetch_worker import FetchWorker
from .dependency_model import DependencyModel, DependencyFilterProxy, row_id
from .recent_files_model import RecentFilesModel


class ProjectController(QObject):
    hasFileChanged = pyqtSignal()
    projectChanged = pyqtSignal()
    recentsChanged = pyqtSignal()
    openError = pyqtSignal(str, str)        # title, body
    fetchingChanged = pyqtSignal()
    statusChanged = pyqtSignal()
    countChanged = pyqtSignal()
    selectionChanged = pyqtSignal()
    progressChanged = pyqtSignal()
    infoMessage = pyqtSignal(str, str)              # title, body
    confirmUpdateAll = pyqtSignal(int, str, str)    # count, mode label, mode key

    def __init__(self, settings: AppSettings, cache: VersionCache | None = None,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._cache = cache if cache is not None else VersionCache()
        self._recent_model = RecentFilesModel(self)

        self._model = DependencyModel(self)
        self._proxy = DependencyFilterProxy(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.set_hide_uptodate(settings.hide_uptodate)
        self._proxy.set_old_threshold(settings.old_version_threshold_days)

        self._file_path: str = ""
        self._deps: list[DependencyInfo] = []
        self._by_rowkey: dict[tuple, DependencyInfo] = {}
        self._pending_install_names: set[str] = set()

        self._thread: QThread | None = None
        self._worker: FetchWorker | None = None
        self._zombie_threads: list = []
        self._is_fetching = False
        self._fetch_completed = 0
        self._fetch_total = 0
        self._status = ""
        self._count_summary = ""
        self._selected_count = 0
        self._selectable_count = 0
        self._header_checked = False

        self._refresh_recents()

    # ── exposed models ───────────────────────────────────────────────────────

    @pyqtProperty(QObject, constant=True)
    def dependencies(self) -> DependencyFilterProxy:
        return self._proxy

    @pyqtProperty(QObject, constant=True)
    def recentFiles(self) -> RecentFilesModel:
        return self._recent_model

    # ── current project ────────────────────────────────────────────────────────

    @pyqtProperty(bool, notify=hasFileChanged)
    def hasFile(self) -> bool:
        return bool(self._file_path)

    @pyqtProperty(str, notify=projectChanged)
    def filePath(self) -> str:
        return self._file_path

    @pyqtProperty(str, notify=projectChanged)
    def projectName(self) -> str:
        return os.path.basename(os.path.dirname(self._file_path)) if self._file_path else ""

    @pyqtProperty(int, notify=projectChanged)
    def depCount(self) -> int:
        return len(self._deps)

    @pyqtProperty(str, notify=projectChanged)
    def projectDir(self) -> str:
        return os.path.dirname(self._file_path) if self._file_path else ""

    @pyqtProperty(bool, notify=fetchingChanged)
    def canUpdateAll(self) -> bool:
        return not self._is_fetching and bool(self._deps)

    # ── status / counts / fetch state ────────────────────────────────────────

    @pyqtProperty(bool, notify=fetchingChanged)
    def isFetching(self) -> bool:
        return self._is_fetching

    @pyqtProperty(float, notify=progressChanged)
    def fetchProgress(self) -> float:
        return (self._fetch_completed / self._fetch_total) if self._fetch_total else 0.0

    @pyqtProperty(str, notify=statusChanged)
    def statusMessage(self) -> str:
        return self._status

    @pyqtProperty(str, notify=countChanged)
    def countSummary(self) -> str:
        return self._count_summary

    @pyqtProperty(int, notify=selectionChanged)
    def selectedCount(self) -> int:
        return self._selected_count

    @pyqtProperty(int, notify=selectionChanged)
    def selectableCount(self) -> int:
        return self._selectable_count

    @pyqtProperty(bool, notify=selectionChanged)
    def headerChecked(self) -> bool:
        return self._header_checked

    # ── recents ────────────────────────────────────────────────────────────────

    @pyqtProperty(bool, notify=recentsChanged)
    def hasRecents(self) -> bool:
        return bool(self._settings.recent_files)

    @pyqtProperty(int, notify=recentsChanged)
    def recentCount(self) -> int:
        return self._recent_model.count()

    @pyqtProperty(QUrl, notify=projectChanged)
    def initialFileDir(self) -> QUrl:
        base = (os.path.dirname(self._settings.last_opened_path)
                if self._settings.last_opened_path else os.path.expanduser("~"))
        return QUrl.fromLocalFile(base)

    @pyqtProperty(QUrl, notify=projectChanged)
    def initialFolderDir(self) -> QUrl:
        base = (os.path.dirname(os.path.dirname(self._settings.last_opened_path))
                if self._settings.last_opened_path else os.path.expanduser("~"))
        return QUrl.fromLocalFile(base)

    # ── open / close ─────────────────────────────────────────────────────────────

    @pyqtSlot(str)
    def openFile(self, path: str) -> None:
        try:
            deps = load_pom(path)
        except Exception as exc:  # noqa: BLE001
            self.openError.emit("Error", f"Could not read pom.xml:\n{exc}")
            return

        self._file_path = path
        self._deps = deps
        self._by_rowkey = {d.row_key: d for d in deps}

        self._settings.last_opened_path = path
        self._settings.add_recent(path)
        self._settings.save()
        self._refresh_recents()

        self._restore_pending(path)
        self._read_pom_names(self._deps)

        self._model.set_deps(self._deps)
        self.projectChanged.emit()
        self.hasFileChanged.emit()
        self._recompute_counts()
        self.startFetch()

    def _restore_pending(self, path: str) -> None:
        """Re-flag dependencies awaiting a resolve, dropping the ones that a
        build outside the app has already downloaded into ~/.m2."""
        remembered = set(self._settings.pending_installs.get(path, []))
        still_pending: set[str] = set()
        for dep in self._deps:
            if dep.name in remembered and not artifact_in_local_repo(
                    dep.name, dep.current_version):
                dep.needs_install = True
                still_pending.add(dep.name)
        self._pending_install_names = still_pending
        if still_pending != remembered:
            self._save_pending()

    @staticmethod
    def _read_pom_names(deps: list[DependencyInfo]) -> None:
        """Label each dependency with the <name> from its own POM in the local
        Maven repository; ones without keep showing their coordinates."""
        for dep in deps:
            dep.pom_name = artifact_pom_name(dep.name, dep.current_version)

    @pyqtSlot(QUrl)
    def openFileUrl(self, url: QUrl) -> None:
        path = url.toLocalFile()
        if path:
            self.openFile(path)

    @pyqtSlot(QUrl)
    def openFolderUrl(self, url: QUrl) -> None:
        folder = url.toLocalFile()
        if not folder:
            return
        candidate = os.path.join(folder, "pom.xml")
        if os.path.isfile(candidate):
            self.openFile(candidate)
        else:
            self.openError.emit("No pom.xml found",
                                f"No pom.xml was found in:\n{folder}")

    @pyqtSlot()
    def closeFile(self) -> None:
        self._cancel_fetch()
        self._file_path = ""
        self._deps = []
        self._by_rowkey = {}
        self._model.set_deps([])
        self._set_status("")
        self.projectChanged.emit()
        self.hasFileChanged.emit()
        self._recompute_counts()
        self._recompute_selection()

    # ── fetch ──────────────────────────────────────────────────────────────────

    @pyqtSlot()
    @pyqtSlot(bool)
    def startRefresh(self, hard: bool = False) -> None:
        self.startFetch(bypass_cache=hard, reload_file=True)

    def startFetch(self, bypass_cache: bool = False, reload_file: bool = False) -> None:
        self._cancel_fetch()
        if (reload_file or bypass_cache) and self._file_path:
            self._reload_deps()
        if not self._deps:
            return

        for dep in self._deps:
            dep.fetch_status = "loading"
            dep.latest_patch = dep.latest_minor = dep.latest_major = None
            dep.patch_age = dep.minor_age = dep.major_age = None
            self._model.update_dep(dep)

        self._fetch_completed = 0
        self._fetch_total = len(self._deps)
        self.progressChanged.emit()
        self._set_fetching(True)
        self._set_status(f"Fetching updates for {len(self._deps)} dependencies…")

        self._worker = FetchWorker(
            self._deps, self._settings.min_age_days,
            cache=self._cache, cache_ttl_hours=self._settings.cache_ttl_hours,
            bypass_cache=bypass_cache,
        )
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._on_fetch_finished)
        self._thread.finished.connect(self._on_thread_cleanup)
        self._worker.package_ready.connect(self._on_package_ready)
        self._worker.progress.connect(self._on_progress)
        self._worker.error.connect(self._on_fetch_error)
        self._thread.start()

    def _reload_deps(self) -> None:
        try:
            new_deps = load_pom(self._file_path)
        except Exception:
            return
        existing = {dep.row_key: dep for dep in self._deps}
        merged = []
        for new_dep in new_deps:
            old = existing.get(new_dep.row_key)
            if old is not None:
                old.raw_constraint = new_dep.raw_constraint
                old.current_version = new_dep.current_version
                merged.append(old)
            else:
                merged.append(new_dep)
        self._deps = merged
        self._by_rowkey = {d.row_key: d for d in merged}
        self._read_pom_names(merged)
        self._model.set_deps(merged)
        self._recompute_counts()

    def _on_package_ready(self, row_key: tuple, updates: dict) -> None:
        dep = self._by_rowkey.get(row_key)
        if dep is None:
            return
        dep.fetch_status = "done"
        dep.latest_patch = updates.get("latest_patch")
        dep.latest_minor = updates.get("latest_minor")
        dep.latest_major = updates.get("latest_major")
        dep.patch_age = updates.get("patch_age")
        dep.minor_age = updates.get("minor_age")
        dep.major_age = updates.get("major_age")
        dep.current_age = updates.get("current_age")
        dep.repo_url = updates.get("repo_url")
        self._model.update_dep(dep)
        self._recompute_counts()

    def _on_progress(self, completed: int, total: int) -> None:
        self._fetch_completed = completed
        self._fetch_total = total
        self.progressChanged.emit()
        self._set_status(f"Fetching updates… {completed}/{total} dependencies checked")

    def _on_fetch_error(self, name: str, message: str) -> None:
        for dep in self._deps:
            if dep.name == name:
                dep.fetch_status = "error"
                dep.error_message = message
                self._model.update_dep(dep)

    def _on_fetch_finished(self) -> None:
        self._set_fetching(False)
        self._recompute_selection()
        self._recompute_counts()

        if self._file_path:
            self._settings.update_last_checked(self._file_path)
            self._refresh_recents()

        has_updates = any(d.has_any_update for d in self._deps)
        errors = sum(1 for d in self._deps if d.fetch_status == "error")
        parts = [f"Done — {len(self._deps)} dependencies checked."]
        if has_updates:
            n = sum(1 for d in self._deps if d.has_any_update)
            parts.append(f"{n} have available updates.")
        else:
            parts.append("All dependencies are up-to-date.")
        if errors:
            parts.append(f"{errors} fetch error(s).")
        self._set_status("  ".join(parts))

    def _cancel_fetch(self) -> None:
        if self._worker:
            self._worker.cancel()
        if self._thread:
            try:
                if self._thread.isRunning():
                    self._thread.quit()
                    self._thread.wait(2000)
                    if self._thread.isRunning():
                        t = self._thread
                        self._zombie_threads.append(t)
                        t.finished.connect(
                            lambda: self._zombie_threads.remove(t)
                            if t in self._zombie_threads else None)
            except RuntimeError:
                pass
        self._worker = None
        self._thread = None

    def _on_thread_cleanup(self) -> None:
        if self._thread is self.sender():
            self._thread = None
            self._worker = None

    # ── single-row update ────────────────────────────────────────────────────

    @pyqtSlot(str, str)
    def updateSingle(self, rid: str, version: str) -> None:
        dep = self._model.dep_by_id(rid)
        if dep is None or not self._file_path:
            return
        try:
            save_pom(self._file_path, [(dep, version)])
        except Exception as exc:  # noqa: BLE001
            self.openError.emit("Error", f"Failed to write pom.xml:\n{exc}")
            return

        self._apply_written_update(dep, version)
        # A shared version property updates every dependency that uses it.
        if dep.property_name is not None:
            for sibling in self._deps:
                if sibling is not dep and sibling.property_name == dep.property_name:
                    self._apply_written_update(sibling, version)
        self._save_pending()

        self._recompute_counts()
        self._recompute_selection()
        self._settings.update_last_checked(self._file_path)
        self._refresh_recents()
        self._set_status(f"✓  {dep.name} updated to {version} — run {self._install_hint()} to apply.")

    def _apply_written_update(self, dep: DependencyInfo, version: str) -> None:
        """Sync one row's state with a version that was just written to disk."""
        self._cache.invalidate(dep.name, dep.current_version)
        if dep.property_name is None:
            dep.raw_constraint = version
        dep.current_version = version
        dep.needs_install = True
        self._pending_install_names.add(dep.name)

        if dep.latest_major == version:
            dep.latest_patch = dep.latest_minor = dep.latest_major = None
            dep.patch_age = dep.minor_age = dep.major_age = None
        elif dep.latest_minor == version:
            dep.latest_patch = dep.latest_minor = None
            dep.patch_age = dep.minor_age = None
        elif dep.latest_patch == version:
            dep.latest_patch = None
            dep.patch_age = None

        self._model.update_dep(dep)

    # ── bulk updates ────────────────────────────────────────────────────────────

    @staticmethod
    def _best(dep: DependencyInfo, mode: str) -> str | None:
        if mode == "patch_minor":
            return dep.latest_minor or dep.latest_patch
        return dep.latest_major or dep.latest_minor or dep.latest_patch

    @pyqtSlot(str)
    def updateSelected(self, mode: str) -> None:
        updates = [(d, t) for d in self._model.selected_deps() if (t := self._best(d, mode))]
        if not updates:
            self.infoMessage.emit(
                "Nothing to update",
                "The selected dependencies have no available updates for the chosen mode.")
            return
        self._write_updates(updates)

    @pyqtSlot(str)
    def requestUpdateAll(self, mode: str) -> None:
        updates = [(d, t) for d in self._deps if (t := self._best(d, mode))]
        if not updates:
            self.infoMessage.emit(
                "Nothing to update",
                "No dependencies have available updates matching the selected mode.")
            return
        label = "Patch & Minor only" if mode == "patch_minor" else "All (including Major)"
        self.confirmUpdateAll.emit(len(updates), label, mode)

    @pyqtSlot(str)
    def applyUpdateAll(self, mode: str) -> None:
        updates = [(d, t) for d in self._deps if (t := self._best(d, mode))]
        if updates:
            self._write_updates(updates)

    def _write_updates(self, updates: list[tuple[DependencyInfo, str]]) -> None:
        if not self._file_path:
            return
        try:
            save_pom(self._file_path, updates)
        except Exception as exc:  # noqa: BLE001
            self.openError.emit("Error", f"Failed to write pom.xml:\n{exc}")
            return
        for dep, new_version in updates:
            self._cache.invalidate(dep.name, dep.current_version)
            self._pending_install_names.add(dep.name)
        self._save_pending()
        self.infoMessage.emit(
            "Updated",
            f"{len(updates)} dependenc{'y' if len(updates) == 1 else 'ies'} updated in pom.xml.\n\n"
            f"Run '{self._install_hint()}' to apply the changes.")
        self.openFile(self._file_path)

    @pyqtSlot()
    def clearPending(self) -> None:
        self._pending_install_names.clear()
        self._save_pending()
        for dep in self._deps:
            if dep.needs_install:
                dep.needs_install = False
                self._model.update_dep(dep)
        self._recompute_selection()

    # ── filters ───────────────────────────────────────────────────────────────

    @pyqtSlot("QVariant")
    def setFilterGroup(self, group) -> None:
        self._proxy.set_group(group if group else None)
        self._recompute_selection()

    @pyqtSlot(bool)
    def setHideUptodate(self, hide: bool) -> None:
        self._proxy.set_hide_uptodate(hide)
        self._settings.hide_uptodate = hide
        self._settings.save()
        self._recompute_selection()

    @pyqtSlot(bool)
    def setOldOnly(self, old_only: bool) -> None:
        self._proxy.set_old_only(old_only)
        self._recompute_selection()

    @pyqtProperty(bool, constant=True)
    def hideUptodateInitial(self) -> bool:
        return self._settings.hide_uptodate

    # ── selection ───────────────────────────────────────────────────────────────

    @pyqtSlot(str, bool)
    def setSelected(self, rid: str, checked: bool) -> None:
        self._model.set_selected(rid, checked)
        self._recompute_selection()

    @pyqtSlot(bool)
    def toggleSelectAll(self, checked: bool) -> None:
        for proxy_row in range(self._proxy.rowCount()):
            src = self._proxy.mapToSource(self._proxy.index(proxy_row, 0)).row()
            dep = self._model.dep_at(src)
            if dep is None:
                continue
            selectable = dep.has_any_update or dep.needs_install or dep.fetch_status != "done"
            if selectable:
                self._model.set_selected(row_id(dep), checked)
        self._recompute_selection()

    # ── recents management ───────────────────────────────────────────────────────

    @pyqtSlot(str)
    def removeRecent(self, path: str) -> None:
        self._settings.recent_files = [
            r for r in self._settings.recent_files if r.get("path") != path
        ]
        self._settings.save()
        self._refresh_recents()

    @pyqtSlot()
    def clearRecents(self) -> None:
        self._settings.recent_files = []
        self._settings.save()
        self._refresh_recents()

    # ── settings coordination ──────────────────────────────────────────────────

    @pyqtSlot()
    def applyDisplaySettings(self) -> None:
        """Re-read display-affecting settings (old-version threshold) into the proxy."""
        self._proxy.set_old_threshold(self._settings.old_version_threshold_days)
        self._recompute_selection()

    @pyqtSlot()
    def refetchForSettings(self) -> None:
        """Re-fetch (bypassing cache) after a setting that invalidates cached data."""
        if self._file_path:
            self.startFetch(bypass_cache=True)

    @pyqtSlot()
    def reopen(self) -> None:
        """Re-read the current pom.xml from disk and re-fetch (e.g. after git pull)."""
        if self._file_path:
            self.openFile(self._file_path)

    # ── lifecycle ─────────────────────────────────────────────────────────────

    @pyqtSlot()
    def shutdown(self) -> None:
        self._cancel_fetch()

    # ── internal ─────────────────────────────────────────────────────────────────

    def _refresh_recents(self) -> None:
        self._recent_model.set_entries(self._settings.recent_files)
        self.recentsChanged.emit()

    def _set_fetching(self, value: bool) -> None:
        if self._is_fetching != value:
            self._is_fetching = value
            self.fetchingChanged.emit()

    def _set_status(self, message: str) -> None:
        if self._status != message:
            self._status = message
            self.statusChanged.emit()

    def _recompute_counts(self) -> None:
        total = len(self._deps)
        done = sum(1 for d in self._deps if d.fetch_status == "done")
        have = sum(1 for d in self._deps if d.has_any_update)
        summary = (f"{total} dependencies  ·  {done} checked  ·  {have} with updates"
                   if total else "")
        if summary != self._count_summary:
            self._count_summary = summary
            self.countChanged.emit()

    def _recompute_selection(self) -> None:
        selected_ids = {row_id(d) for d in self._model.selected_deps()}
        selectable = 0
        selected = 0
        for proxy_row in range(self._proxy.rowCount()):
            src = self._proxy.mapToSource(self._proxy.index(proxy_row, 0)).row()
            dep = self._model.dep_at(src)
            if dep is None:
                continue
            can = (not self._is_fetching
                   and (dep.has_any_update or dep.needs_install or dep.fetch_status != "done"))
            if can:
                selectable += 1
                if row_id(dep) in selected_ids:
                    selected += 1
        header = selectable > 0 and selected == selectable
        if (selectable, selected, header) != (
                self._selectable_count, self._selected_count, self._header_checked):
            self._selectable_count = selectable
            self._selected_count = selected
            self._header_checked = header
            self.selectionChanged.emit()

    def _save_pending(self) -> None:
        if not self._file_path:
            return
        if self._pending_install_names:
            self._settings.pending_installs[self._file_path] = list(self._pending_install_names)
        else:
            self._settings.pending_installs.pop(self._file_path, None)
        self._settings.save()

    def _install_hint(self) -> str:
        """The resolve command for the current project's build tool,
        e.g. 'mvn dependency:resolve'."""
        directory = os.path.dirname(self._file_path) if self._file_path else ""
        return " ".join(self._settings.active_build_tool(directory).install_cmd())
