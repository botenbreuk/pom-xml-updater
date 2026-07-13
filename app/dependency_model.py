"""
Model layer for the dependency table.

``DependencyModel`` exposes one :class:`DependencyInfo` per row with all the
roles the QML delegate needs; ``DependencyFilterProxy`` applies the group /
hide-up-to-date / old-only filters.  Theming and age formatting are done in
QML — this layer is data-only.
"""
from __future__ import annotations

from PyQt6.QtCore import (
    QAbstractListModel, QModelIndex, QSortFilterProxyModel, Qt,
)

from models.dependency import DependencyInfo

# ── version-definition type detection ──────────────────────────────────────────

_TYPE_LABEL = {
    "property": "Property", "exact": "Exact", "snapshot": "Snapshot",
    "range": "Range",
}


def constraint_type(raw: str) -> str:
    s = raw.strip()
    if s.startswith("${"):
        return "property"
    if s and s[0] in "[(":
        return "range"
    if s.upper().endswith("-SNAPSHOT"):
        return "snapshot"
    return "exact"


def repo_label(url: str) -> str:
    u = url.lower()
    if "github.com" in u:
        return "GitHub ↗"
    if "gitlab.com" in u:
        return "GitLab ↗"
    if "bitbucket.org" in u:
        return "Bitbucket ↗"
    return "repo ↗"


# ── roles ──────────────────────────────────────────────────────────────────────

_ROLE_NAMES = [
    "rowId", "name", "propertyName", "group", "groupLabel", "rawConstraint",
    "currentVersion", "constraintType", "constraintTypeLabel", "currentAge",
    "needsInstall", "repoUrl", "repoLabel", "centralUrl", "fetchStatus",
    "errorMessage", "patchVersion", "minorVersion", "majorVersion", "patchAge",
    "minorAge", "majorAge", "selected", "selectable",
]
_BASE = int(Qt.ItemDataRole.UserRole)
ROLE = {name: _BASE + i for i, name in enumerate(_ROLE_NAMES)}


def row_id(dep: DependencyInfo) -> str:
    return f"{dep.name}\x00{dep.group}\x00{dep.property_name}"


def _age(value) -> int:
    return -1 if value is None else int(value)


def _central_url(name: str) -> str:
    group_id, _, artifact_id = name.partition(":")
    return f"https://central.sonatype.com/artifact/{group_id}/{artifact_id}"


class DependencyModel(QAbstractListModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._deps: list[DependencyInfo] = []
        self._index: dict[str, int] = {}
        self._selected: set[str] = set()

    def roleNames(self):
        return {rid: name.encode() for name, rid in ROLE.items()}

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._deps)

    def dep_at(self, row: int) -> DependencyInfo | None:
        return self._deps[row] if 0 <= row < len(self._deps) else None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._deps)):
            return None
        dep = self._deps[index.row()]
        rid = row_id(dep)
        if role == ROLE["rowId"]:
            return rid
        if role == ROLE["name"]:
            return dep.name
        if role == ROLE["propertyName"]:
            return dep.property_name or ""
        if role == ROLE["group"]:
            return dep.group
        if role == ROLE["groupLabel"]:
            return dep.group_label
        if role == ROLE["rawConstraint"]:
            return dep.raw_constraint
        if role == ROLE["currentVersion"]:
            return dep.current_version
        if role == ROLE["constraintType"]:
            return constraint_type(dep.raw_constraint)
        if role == ROLE["constraintTypeLabel"]:
            key = constraint_type(dep.raw_constraint)
            return _TYPE_LABEL.get(key, key.capitalize())
        if role == ROLE["currentAge"]:
            return _age(dep.current_age)
        if role == ROLE["needsInstall"]:
            return dep.needs_install
        if role == ROLE["repoUrl"]:
            return dep.repo_url or ""
        if role == ROLE["repoLabel"]:
            return repo_label(dep.repo_url) if dep.repo_url else ""
        if role == ROLE["centralUrl"]:
            return _central_url(dep.name)
        if role == ROLE["fetchStatus"]:
            return dep.fetch_status
        if role == ROLE["errorMessage"]:
            return dep.error_message
        if role == ROLE["patchVersion"]:
            return dep.latest_patch or ""
        if role == ROLE["minorVersion"]:
            return dep.latest_minor or ""
        if role == ROLE["majorVersion"]:
            return dep.latest_major or ""
        if role == ROLE["patchAge"]:
            return _age(dep.patch_age)
        if role == ROLE["minorAge"]:
            return _age(dep.minor_age)
        if role == ROLE["majorAge"]:
            return _age(dep.major_age)
        if role == ROLE["selected"]:
            return rid in self._selected
        if role == ROLE["selectable"]:
            return dep.has_any_update or dep.needs_install or dep.fetch_status != "done"
        return None

    # ── mutation ─────────────────────────────────────────────────────────────

    def set_deps(self, deps: list[DependencyInfo]) -> None:
        self.beginResetModel()
        self._deps = list(deps)
        self._index = {row_id(d): i for i, d in enumerate(self._deps)}
        self._selected.clear()
        self.endResetModel()

    def update_dep(self, dep: DependencyInfo) -> None:
        row = self._index.get(row_id(dep))
        if row is None:
            return
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx)

    def dep_by_id(self, rid: str) -> DependencyInfo | None:
        row = self._index.get(rid)
        return self._deps[row] if row is not None else None

    def set_selected(self, rid: str, checked: bool) -> None:
        if checked:
            self._selected.add(rid)
        else:
            self._selected.discard(rid)
        row = self._index.get(rid)
        if row is not None:
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [ROLE["selected"]])

    def clear_selection(self) -> None:
        self._selected.clear()
        if self._deps:
            self.dataChanged.emit(self.index(0, 0),
                                  self.index(len(self._deps) - 1, 0),
                                  [ROLE["selected"]])

    def selected_deps(self) -> list[DependencyInfo]:
        return [d for d in self._deps if row_id(d) in self._selected]


class DependencyFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._group: str | None = None
        self._hide_uptodate = False
        self._old_only = False
        self._old_threshold = 0

    def set_group(self, group: str | None) -> None:
        self._group = group or None
        self.invalidateFilter()

    def set_hide_uptodate(self, hide: bool) -> None:
        self._hide_uptodate = bool(hide)
        self.invalidateFilter()

    def set_old_only(self, old_only: bool) -> None:
        self._old_only = bool(old_only)
        self.invalidateFilter()

    def set_old_threshold(self, days: int) -> None:
        self._old_threshold = int(days)
        if self._old_only:
            self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, parent: QModelIndex) -> bool:
        model = self.sourceModel()
        dep = model.dep_at(source_row)
        if dep is None:
            return False

        if self._group and dep.group != self._group:
            return False

        if self._hide_uptodate:
            if (dep.fetch_status == "done" and not dep.has_any_update
                    and not dep.needs_install):
                return False

        if self._old_only:
            is_old = (dep.current_age is not None and self._old_threshold > 0
                      and dep.current_age >= self._old_threshold)
            if dep.fetch_status not in ("loading", "pending") and not is_old:
                return False

        return True
