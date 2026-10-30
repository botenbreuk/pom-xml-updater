"""
Tests for the persisted dependency-table column widths: the ``column_widths``
map on AppSettings and the AppController API the table seeds from and saves to,
plus the longest versions ProjectController reports so the update columns never
get narrower than them.

Storage is isolated to a temp config dir per test, so nothing here can read or
clobber the developer's own settings.ini.

Run from the repo root with:

    python -m unittest tests.test_column_widths
"""
from __future__ import annotations

import os
import tempfile
import unittest

from PyQt6.QtCore import QCoreApplication

from app.app_controller import AppController
from app.dependency_model import row_id
from app.project_controller import ProjectController
from core.version_cache import VersionCache
from models.dependency import DependencyInfo
from models.settings import AppSettings

_app = QCoreApplication.instance() or QCoreApplication([])


class IsolatedSettingsTest(unittest.TestCase):
    """Redirects AppSettings' storage to a throwaway directory per test."""

    def setUp(self) -> None:
        cfg = tempfile.TemporaryDirectory(); self.addCleanup(cfg.cleanup)
        env_vars = ("XDG_CONFIG_HOME", "APPDATA", "XDG_CACHE_HOME")
        backup = {v: os.environ.get(v) for v in env_vars}
        for v in env_vars:
            os.environ[v] = cfg.name

        def restore() -> None:
            for v, val in backup.items():
                if val is None:
                    os.environ.pop(v, None)
                else:
                    os.environ[v] = val

        self.addCleanup(restore)

    @staticmethod
    def fresh_loaded() -> AppSettings:
        """A brand-new AppSettings populated from whatever is on disk."""
        s = AppSettings()
        s.load()
        return s


# ── AppSettings ──────────────────────────────────────────────────────────────

class TestColumnWidthSettings(IsolatedSettingsTest):
    def test_defaults_to_empty(self) -> None:
        self.assertEqual(AppSettings().column_widths, {})
        self.assertEqual(self.fresh_loaded().column_widths, {})

    def test_set_persists_immediately(self) -> None:
        AppSettings().set_column_widths({"group": 90, "major": 182.5})
        self.assertEqual(self.fresh_loaded().column_widths,
                         {"group": 90.0, "major": 182.5})

    def test_set_drops_invalid_entries(self) -> None:
        s = AppSettings()
        s.set_column_widths({"group": 90, "current": 0, "type": -10,
                             "patch": "wide", "minor": True, "major": float("inf")})
        self.assertEqual(s.column_widths, {"group": 90.0})
        self.assertEqual(self.fresh_loaded().column_widths, {"group": 90.0})

    def test_invalid_stored_entries_are_dropped_on_load(self) -> None:
        s = AppSettings()
        s.column_widths = {"group": 90, "current": "wide", "type": None}
        s.save()
        self.assertEqual(self.fresh_loaded().column_widths, {"group": 90.0})

    def test_stored_non_map_loads_as_empty(self) -> None:
        s = AppSettings()
        s.column_widths = [120, 150]
        s.save()
        self.assertEqual(self.fresh_loaded().column_widths, {})


# ── AppController ────────────────────────────────────────────────────────────

class TestAppControllerColumnWidths(IsolatedSettingsTest):
    def test_initial_widths_come_from_settings(self) -> None:
        AppSettings().set_column_widths({"type": 96})
        appc = AppController(self.fresh_loaded(), VersionCache())
        self.addCleanup(appc.shutdown)
        self.assertEqual(appc.columnWidthsInitial, {"type": 96.0})

    def test_set_persists_without_flash(self) -> None:
        appc = AppController(self.fresh_loaded(), VersionCache())
        self.addCleanup(appc.shutdown)
        flashes: list[str] = []
        appc.flash.connect(flashes.append)

        appc.setColumnWidths({"current": 120, "major": 200})

        self.assertEqual(self.fresh_loaded().column_widths,
                         {"current": 120.0, "major": 200.0})
        self.assertEqual(flashes, [])


# ── ProjectController ────────────────────────────────────────────────────────

def _dep(name: str, patch: str | None = None, minor: str | None = None,
         major: str | None = None) -> DependencyInfo:
    dep = DependencyInfo(f"org.example:{name}", "dependencies", "1.2.3", "1.2.3")
    dep.latest_patch, dep.latest_minor, dep.latest_major = patch, minor, major
    dep.fetch_status = "done"
    return dep


class TestLongestVersions(IsolatedSettingsTest):
    def setUp(self) -> None:
        super().setUp()
        self.project = ProjectController(self.fresh_loaded(), VersionCache())
        self.changes: list[int] = []
        self.project.longestVersionsChanged.connect(lambda: self.changes.append(1))

    def show_deps(self, *deps: DependencyInfo, path: str = "/app/pom.xml") -> None:
        self.project._file_path = path
        self.project._deps = list(deps)
        self.project._model.set_deps(self.project._deps)

    def test_empty_without_versions(self) -> None:
        self.assertEqual(self.project.longestVersions,
                         {"patch": "", "minor": "", "major": ""})

    def test_longest_version_per_column(self) -> None:
        self.show_deps(_dep("a", patch="1.2.10", minor="1.3.0", major="2.0.0"),
                       _dep("b", patch="1.2.4", minor="1.10.0-SNAPSHOT"),
                       _dep("c", major="10.0.0.Final"))
        self.assertEqual(self.project.longestVersions,
                         {"patch": "1.2.10", "minor": "1.10.0-SNAPSHOT", "major": "10.0.0.Final"})
        self.assertEqual(len(self.changes), 1)

    def test_follows_row_updates(self) -> None:
        dep = _dep("a", patch="1.2.4")
        self.show_deps(dep)
        dep.latest_patch = "1.2.10"
        self.project._model.update_dep(dep)
        self.assertEqual(self.project.longestVersions["patch"], "1.2.10")
        self.assertEqual(len(self.changes), 2)

    def test_refetch_only_grows_until_every_version_is_back(self) -> None:
        a, b = _dep("a", patch="1.2.10"), _dep("b", patch="1.2.4")
        self.show_deps(a, b)
        for dep in (a, b):
            dep.fetch_status, dep.latest_patch = "loading", None
            self.project._model.update_dep(dep)
        self.assertEqual(self.project.longestVersions["patch"], "1.2.10")

        a.fetch_status, a.latest_patch = "done", "1.2.11"
        self.project._model.update_dep(a)
        self.assertEqual(self.project.longestVersions["patch"], "1.2.11")

        a.latest_patch = "1.2.5"
        self.project._model.update_dep(a)
        self.assertEqual(self.project.longestVersions["patch"], "1.2.11")

        b.fetch_status = "done"
        self.project._model.update_dep(b)
        self.assertEqual(self.project.longestVersions["patch"], "1.2.5")

    def test_reopening_the_project_keeps_the_versions_until_refetched(self) -> None:
        self.show_deps(_dep("a", patch="1.2.10"))
        reloaded = _dep("a")
        reloaded.fetch_status = "pending"
        self.show_deps(reloaded)
        self.assertEqual(self.project.longestVersions["patch"], "1.2.10")

        reloaded.fetch_status, reloaded.latest_patch = "done", "1.2.5"
        self.project._model.update_dep(reloaded)
        self.assertEqual(self.project.longestVersions["patch"], "1.2.5")

    def test_opening_another_project_starts_over(self) -> None:
        self.show_deps(_dep("a", patch="1.2.10"))
        other = _dep("b")
        other.fetch_status = "pending"
        self.show_deps(other, path="/other/pom.xml")
        self.assertEqual(self.project.longestVersions["patch"], "")

    def test_signals_only_when_a_longest_version_changes(self) -> None:
        dep = _dep("a", patch="1.2.4")
        self.show_deps(dep)
        self.changes.clear()
        self.project.setSelected(row_id(dep), True)
        self.assertEqual(self.changes, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
