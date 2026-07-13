"""
List model of recently-opened projects for the QML start screen.

Holds only entries whose ``pom.xml`` still exists on disk; the owning
controller separately tracks whether any recents ever existed (to choose
between the list and the "no recent files" empty state).
"""
from __future__ import annotations

import os
from datetime import datetime

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt

PATH_ROLE = Qt.ItemDataRole.UserRole
DISPLAY_PATH_ROLE = Qt.ItemDataRole.UserRole + 1
PROJECT_NAME_ROLE = Qt.ItemDataRole.UserRole + 2
AGE_TEXT_ROLE = Qt.ItemDataRole.UserRole + 3


class RecentFilesModel(QAbstractListModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._entries: list[dict] = []

    def roleNames(self):
        return {
            PATH_ROLE: b"path",
            DISPLAY_PATH_ROLE: b"displayPath",
            PROJECT_NAME_ROLE: b"projectName",
            AGE_TEXT_ROLE: b"ageText",
        }

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._entries)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._entries)):
            return None
        entry = self._entries[index.row()]
        path = entry.get("path", "")
        if role == PATH_ROLE:
            return path
        if role == DISPLAY_PATH_ROLE:
            return _shorten_path(path)
        if role == PROJECT_NAME_ROLE:
            return os.path.basename(os.path.dirname(path))
        if role == AGE_TEXT_ROLE:
            return _fmt_age(entry.get("last_checked"))
        return None

    def set_entries(self, entries: list[dict]) -> None:
        """Replace the rows with the on-disk subset of *entries*."""
        valid = [e for e in entries if os.path.isfile(e.get("path", ""))]
        self.beginResetModel()
        self._entries = valid
        self.endResetModel()

    def count(self) -> int:
        return len(self._entries)


# ── module helpers (ported from ui/start_screen.py) ────────────────────────────

def _shorten_path(path: str, max_len: int = 55) -> str:
    home = os.path.expanduser("~")
    if path.startswith(home):
        path = "~" + path[len(home):]
    if len(path) <= max_len:
        return path
    parts = path.split(os.sep)
    if len(parts) > 3:
        return os.sep.join(["…"] + parts[-2:])
    return path


def _fmt_age(iso_str: str | None) -> str:
    if not iso_str:
        return "Never checked"
    try:
        diff = datetime.now() - datetime.fromisoformat(iso_str)
        days = diff.days
        hours = diff.seconds // 3600
        mins = diff.seconds // 60
        if days == 0:
            if mins == 0:
                return "Checked just now"
            if hours == 0:
                return f"Checked {mins}m ago"
            return f"Checked {hours}h ago"
        if days == 1:
            return "Checked yesterday"
        if days < 30:
            return f"Checked {days} days ago"
        months = days // 30
        if days < 365:
            return f"Checked {months}mo ago"
        years = days // 365
        return f"Checked {years}y ago"
    except Exception:
        return "Checked recently"
