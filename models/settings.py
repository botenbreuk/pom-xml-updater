from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QSettings

from core.build_tool import DEFAULT_TOOL, BuildTool, Detection, detect

ORG = "42nl"
APP = "PomXmlUpdater"
_MAX_RECENT = 10


def _make_settings() -> QSettings:
    """Return a QSettings instance pointing at the right location per platform."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    path = base / APP / "settings.ini"
    path.parent.mkdir(parents=True, exist_ok=True)
    return QSettings(str(path), QSettings.Format.IniFormat)


def _system_is_dark() -> bool:
    """Return True when the OS is currently in dark mode."""
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        pass
    # Fallback: infer from palette window-text lightness
    try:
        from PyQt6.QtGui import QPalette
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            return app.palette().color(QPalette.ColorRole.WindowText).lightness() > 128
    except Exception:
        pass
    return False


@dataclass
class AppSettings:
    min_age_days: int = 2
    cache_ttl_hours: int = 24
    last_opened_path: str = ""
    theme: str = "system"          # "light" | "dark" | "system"
    hide_uptodate: bool = True
    merge_patch_minor: bool = False
    recent_files: list = field(default_factory=list)
    # Each entry: {"path": str, "last_checked": str | None}
    pending_installs: dict = field(default_factory=dict)
    # {"path/to/pom.xml": ["group:artifact", ...]}
    default_build_tool: str = "mvn"    # global fallback: mvn | mvnw | mvnd
    build_tool_overrides: dict = field(default_factory=dict)
    # {"path/to/project-dir": "mvn" | "mvnw" | "mvnd"}
    old_version_threshold: int = 12   # number of months or years (0 = disabled)
    old_version_unit: str = "months"  # "months" | "years"
    column_widths: dict = field(default_factory=dict)
    # {"group": 74.0, "major": 180.0, ...} — dependency-table columns, in pixels

    # ── resolved theme ────────────────────────────────────────────────────────

    @property
    def old_version_threshold_days(self) -> int:
        """Threshold in days (0 when disabled)."""
        if self.old_version_threshold <= 0:
            return 0
        if self.old_version_unit == "years":
            return self.old_version_threshold * 365
        return self.old_version_threshold * 30

    @property
    def dark_mode(self) -> bool:
        """Resolved dark/light boolean — callers never need to check theme directly."""
        if self.theme == "dark":
            return True
        if self.theme == "light":
            return False
        return _system_is_dark()

    # ── recent-file helpers ───────────────────────────────────────────────────

    def add_recent(self, path: str) -> None:
        """Insert *path* at the front of the recent list (deduped, max _MAX_RECENT)."""
        self.recent_files = [r for r in self.recent_files if r.get("path") != path]
        self.recent_files.insert(0, {"path": path, "last_checked": None})
        self.recent_files = self.recent_files[:_MAX_RECENT]

    def update_last_checked(self, path: str) -> None:
        """Stamp *path* with the current time and persist immediately."""
        for entry in self.recent_files:
            if entry.get("path") == path:
                entry["last_checked"] = datetime.now().isoformat()
                break
        self.save()

    # ── build-tool selection ──────────────────────────────────────────────────

    def build_tool_override(self, project_dir: str) -> str | None:
        """Return the pinned tool id for *project_dir*, or None if unset."""
        return self.build_tool_overrides.get(project_dir)

    def set_build_tool_override(self, project_dir: str, tool_id: str) -> None:
        """Pin *project_dir* to *tool_id* (validated) and persist immediately."""
        tool = BuildTool.from_id(tool_id)
        if tool is None or not project_dir:
            return
        self.build_tool_overrides[project_dir] = tool.id
        self.save()

    def clear_build_tool_override(self, project_dir: str) -> None:
        """Remove any pin for *project_dir* and persist if something changed."""
        if self.build_tool_overrides.pop(project_dir, None) is not None:
            self.save()

    def resolve_build_tool(self, project_dir: str) -> Detection:
        """Full detection for *project_dir*, honoring its override and the
        global default."""
        return detect(
            project_dir,
            override=self.build_tool_override(project_dir),
            default=self.default_build_tool,
        )

    def active_build_tool(self, project_dir: str) -> BuildTool:
        """Concrete tool for driving CLI commands — never None."""
        return self.resolve_build_tool(project_dir).tool

    @staticmethod
    def _sanitize_tool(value: str) -> str:
        """Coerce a stored tool id to a supported one, defaulting to mvn."""
        return (BuildTool.from_id(value) or DEFAULT_TOOL).id

    @staticmethod
    def _sanitize_overrides(raw) -> dict:
        """Keep only override entries that name a supported build tool."""
        if not isinstance(raw, dict):
            return {}
        clean: dict = {}
        for path, value in raw.items():
            tool = BuildTool.from_id(value)
            if tool is not None:
                clean[str(path)] = tool.id
        return clean

    # ── table column widths ───────────────────────────────────────────────────

    def set_column_widths(self, widths: dict) -> None:
        """Store the dependency-table column widths (validated) and persist
        immediately."""
        self.column_widths = self._sanitize_column_widths(widths)
        self.save()

    @staticmethod
    def _sanitize_column_widths(raw) -> dict:
        """Keep only entries whose width is a positive, finite number."""
        if not isinstance(raw, dict):
            return {}
        return {
            str(name): float(width)
            for name, width in raw.items()
            if isinstance(width, (int, float)) and not isinstance(width, bool)
            and math.isfinite(width) and width > 0
        }

    # ── persistence ───────────────────────────────────────────────────────────

    def load(self) -> None:
        s = _make_settings()
        self.min_age_days     = int(s.value("min_age_days",     self.min_age_days))
        self.cache_ttl_hours  = int(s.value("cache_ttl_hours",  self.cache_ttl_hours))
        self.last_opened_path = str(s.value("last_opened_path", self.last_opened_path))
        self.hide_uptodate      = s.value("hide_uptodate",      self.hide_uptodate,      type=bool)
        self.merge_patch_minor  = s.value("merge_patch_minor",  self.merge_patch_minor,  type=bool)
        self.old_version_threshold = int(s.value("old_version_threshold", self.old_version_threshold))
        raw_unit = str(s.value("old_version_unit", self.old_version_unit))
        self.old_version_unit = raw_unit if raw_unit in ("months", "years") else "months"
        try:
            self.recent_files = json.loads(s.value("recent_files", "[]"))
        except Exception:
            self.recent_files = []
        try:
            self.pending_installs = json.loads(s.value("pending_installs", "{}"))
        except Exception:
            self.pending_installs = {}

        self.default_build_tool = self._sanitize_tool(
            str(s.value("default_build_tool", self.default_build_tool)))
        try:
            raw_overrides = json.loads(s.value("build_tool_overrides", "{}"))
        except Exception:
            raw_overrides = {}
        self.build_tool_overrides = self._sanitize_overrides(raw_overrides)

        try:
            raw_widths = json.loads(s.value("column_widths", "{}"))
        except Exception:
            raw_widths = {}
        self.column_widths = self._sanitize_column_widths(raw_widths)

        raw_theme = s.value("theme", None)
        if raw_theme in ("light", "dark", "system"):
            self.theme = raw_theme
        # else: keep dataclass default ("system")

    def save(self) -> None:
        s = _make_settings()
        s.setValue("min_age_days",     self.min_age_days)
        s.setValue("cache_ttl_hours",  self.cache_ttl_hours)
        s.setValue("last_opened_path", self.last_opened_path)
        s.setValue("theme",            self.theme)
        s.setValue("hide_uptodate",          self.hide_uptodate)
        s.setValue("merge_patch_minor",      self.merge_patch_minor)
        s.setValue("old_version_threshold",  self.old_version_threshold)
        s.setValue("old_version_unit",       self.old_version_unit)
        s.setValue("recent_files",     json.dumps(self.recent_files))
        s.setValue("pending_installs", json.dumps(self.pending_installs))
        s.setValue("default_build_tool",    self.default_build_tool)
        s.setValue("build_tool_overrides",  json.dumps(self.build_tool_overrides))
        s.setValue("column_widths",         json.dumps(self.column_widths))
