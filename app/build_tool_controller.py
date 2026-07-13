"""
Controller that tracks the active build tool for the open project and drives
the picker dialog.  Exposed to QML as the ``BuildTool`` context property.

The heavy lifting (detection + persistence) lives in ``core.build_tool`` and
``AppSettings``; this class just holds the current selection, tells QML when
to open the picker, and applies the user's choice.
"""
from __future__ import annotations

import os
import shutil
import sys

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from core.build_tool import BuildTool as Tool, find_wrapper_dir
from core.java_env import java_path_env
from models.settings import AppSettings


class BuildToolController(QObject):
    activeChanged = pyqtSignal()
    overridesChanged = pyqtSignal()       # a per-folder pin was added/changed
    showPicker = pyqtSignal(str)          # currentId — ask QML to open the dialog

    def __init__(self, settings: AppSettings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._project_dir = ""
        self._active = settings.active_build_tool("")   # global default at startup

    # ── exposed state ─────────────────────────────────────────────────────────

    @pyqtProperty(str, notify=activeChanged)
    def activeId(self) -> str:
        return self._active.id

    @pyqtProperty(str, notify=activeChanged)
    def activeName(self) -> str:
        return self._active.display

    @pyqtProperty(str, notify=activeChanged)
    def installCommand(self) -> str:
        return " ".join(self._active.install_cmd())

    @pyqtProperty(str, notify=activeChanged)
    def projectDir(self) -> str:
        return self._project_dir

    @pyqtProperty(bool, notify=activeChanged)
    def hasOverride(self) -> bool:
        return bool(self._project_dir) and \
            self._settings.build_tool_override(self._project_dir) is not None

    # ── project tracking ──────────────────────────────────────────────────────

    @pyqtSlot(str)
    def setProject(self, project_dir: str) -> None:
        """Point at *project_dir* and re-resolve the build tool.  Detection is
        never ambiguous for Maven (a wrapper script wins over the default), so
        the picker only opens on demand from the toolbar badge."""
        if project_dir == self._project_dir:
            return
        self._project_dir = project_dir
        self._active = self._settings.active_build_tool(project_dir)
        self.activeChanged.emit()

    @pyqtSlot()
    def reevaluate(self) -> None:
        """Re-resolve the active tool for the current project without
        prompting — e.g. after the default or an override changed in Settings."""
        self._active = self._settings.active_build_tool(self._project_dir)
        self.activeChanged.emit()

    # ── picker ────────────────────────────────────────────────────────────────

    @pyqtSlot()
    def requestPicker(self) -> None:
        """Open the picker on demand (from the toolbar badge)."""
        self.showPicker.emit(self._active.id)

    @pyqtSlot(str, bool)
    def choose(self, tool_id: str, remember: bool) -> None:
        """Apply the user's pick.  When *remember* is set, pin it to this folder;
        otherwise it applies only for the current session."""
        tool = Tool.from_id(tool_id)
        if tool is None:
            return
        if remember and self._project_dir:
            self._settings.set_build_tool_override(self._project_dir, tool.id)
            self.overridesChanged.emit()
        self._active = tool
        self.activeChanged.emit()

    @pyqtSlot(result="QVariantMap")
    def detectedTools(self) -> dict:
        """``{tool_id: marker}`` describing where each tool was found — the
        wrapper script name for mvnw, "on PATH" for mvn / mvnd.  Used by the
        dialog to show what is available."""
        found: dict[str, str] = {}
        if self._project_dir:
            wrapper_dir = find_wrapper_dir(self._project_dir)
            if wrapper_dir is not None:
                script = "mvnw.cmd" if sys.platform == "win32" else "mvnw"
                if not os.path.isfile(os.path.join(wrapper_dir, script)):
                    script = "mvnw.cmd" if script == "mvnw" else "mvnw"
                found[Tool.WRAPPER.id] = script
        path_env = java_path_env().get("PATH", "")
        for tool in (Tool.MAVEN, Tool.MVND):
            if shutil.which(tool.binary, path=path_env):
                found[tool.id] = "on PATH"
        return found
