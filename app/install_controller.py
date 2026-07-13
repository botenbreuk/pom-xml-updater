"""
Controller that runs the active build tool's resolve command in the project
directory and streams the output live to the QML overlay.  Exposed to QML as
the ``Install`` property.
"""
from __future__ import annotations

import re
import shutil
import sys

from PyQt6.QtCore import (
    QObject, QProcess, QProcessEnvironment, pyqtProperty, pyqtSignal, pyqtSlot,
)

from core.java_env import java_path_env
from core.build_tool import BuildTool, wrapper_script_path
from models.settings import AppSettings

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\][^\x07]*\x07|\x1b[()][AB012]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


class InstallController(QObject):
    runningChanged = pyqtSignal()
    statusChanged = pyqtSignal()
    outputChanged = pyqtSignal()
    succeeded = pyqtSignal()

    def __init__(self, settings: AppSettings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._process: QProcess | None = None
        self._tool: BuildTool | None = None
        self._running = False
        self._status = "running"          # running | ok | error
        self._status_text = ""
        self._output = ""

    @pyqtProperty(bool, notify=runningChanged)
    def running(self) -> bool:
        return self._running

    @pyqtProperty(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @pyqtProperty(str, notify=statusChanged)
    def statusText(self) -> str:
        return self._status_text

    @pyqtProperty(str, notify=outputChanged)
    def output(self) -> str:
        return self._output

    @pyqtSlot(str)
    def start(self, project_dir: str) -> None:
        tool = self._settings.active_build_tool(project_dir)
        self._tool = tool

        self._output = ""
        self.outputChanged.emit()
        self._set_status("running", f"Running {' '.join(tool.install_cmd())}…")

        self._process = QProcess(self)
        self._process.setWorkingDirectory(project_dir)

        env = java_path_env()
        proc_env = QProcessEnvironment.systemEnvironment()
        proc_env.insert("PATH", env["PATH"])
        if env.get("JAVA_HOME"):
            proc_env.insert("JAVA_HOME", env["JAVA_HOME"])
        self._process.setProcessEnvironment(proc_env)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_output)
        self._process.finished.connect(self._on_finished)

        program, args = self._invocation(tool, env["PATH"], project_dir)
        self._set_running(True)
        self._process.start(program, args)

        if not self._process.waitForStarted(3000):
            self._on_failed_to_start()

    @staticmethod
    def _invocation(tool: BuildTool, path_env: str,
                    project_dir: str) -> tuple[str, list[str]]:
        """Build the (program, args) to run the tool's resolve for this platform."""
        argv = tool.install_cmd()
        if tool is BuildTool.WRAPPER:
            script = wrapper_script_path(project_dir) or argv[0]
            if sys.platform == "win32":
                return "cmd.exe", ["/c", script, *argv[1:]]
            return script, argv[1:]
        if sys.platform == "win32":
            return "cmd.exe", ["/c", *argv]
        program = shutil.which(tool.binary, path=path_env) or tool.binary
        return program, argv[1:]

    @pyqtSlot()
    def stop(self) -> None:
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
            self._process.waitForFinished(2000)

    @pyqtSlot()
    def shutdown(self) -> None:
        self.stop()

    # ── process callbacks ────────────────────────────────────────────────────

    def _on_output(self) -> None:
        raw = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._output += _strip_ansi(raw)
        self.outputChanged.emit()

    def _on_finished(self, exit_code: int, _exit_status) -> None:
        self._set_running(False)
        if exit_code == 0:
            self._set_status("ok", "✓   Done — dependencies resolved successfully")
            self.succeeded.emit()
        else:
            self._set_status("error", f"✕   Failed (exit code {exit_code})")

    def _on_failed_to_start(self) -> None:
        self._set_running(False)
        name = self._tool.display if self._tool else "the build tool"
        self._set_status("error", f"✕   Could not start {name} — is it installed and on PATH?")

    # ── helpers ──────────────────────────────────────────────────────────────

    def _set_running(self, value: bool) -> None:
        if self._running != value:
            self._running = value
            self.runningChanged.emit()

    def _set_status(self, status: str, text: str) -> None:
        self._status = status
        self._status_text = text
        self.statusChanged.emit()
