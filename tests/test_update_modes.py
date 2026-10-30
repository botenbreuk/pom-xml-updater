"""
Tests for the bulk-update modes behind the Update Selected / Update All split
buttons: which version each mode picks for a dependency, and what the Update
All confirmation reports.

The controller is built on an unloaded AppSettings and nothing here saves, so
the developer's own settings.ini is never read or written.

Run from the repo root with:

    python -m unittest tests.test_update_modes
"""
from __future__ import annotations

import unittest

from PyQt6.QtCore import QCoreApplication

from app.project_controller import ProjectController
from core.version_cache import VersionCache
from models.dependency import DependencyInfo
from models.settings import AppSettings

_app = QCoreApplication.instance() or QCoreApplication([])


def _dep(name: str, patch: str | None = None, minor: str | None = None,
         major: str | None = None) -> DependencyInfo:
    dep = DependencyInfo(f"org.example:{name}", "dependencies", "1.2.3", "1.2.3")
    dep.latest_patch, dep.latest_minor, dep.latest_major = patch, minor, major
    return dep


# ── per-dependency version choice ────────────────────────────────────────────

class TestBestVersion(unittest.TestCase):
    def test_patch_mode_takes_only_the_patch(self) -> None:
        dep = _dep("a", patch="1.2.9", minor="1.5.0", major="2.0.0")
        self.assertEqual(ProjectController._best(dep, "patch"), "1.2.9")

    def test_patch_mode_skips_deps_without_a_patch(self) -> None:
        dep = _dep("a", minor="1.5.0", major="2.0.0")
        self.assertIsNone(ProjectController._best(dep, "patch"))

    def test_patch_minor_mode_prefers_minor_then_patch(self) -> None:
        both = _dep("a", patch="1.2.9", minor="1.5.0", major="2.0.0")
        patch_only = _dep("b", patch="1.2.9", major="2.0.0")
        self.assertEqual(ProjectController._best(both, "patch_minor"), "1.5.0")
        self.assertEqual(ProjectController._best(patch_only, "patch_minor"), "1.2.9")

    def test_all_mode_prefers_the_highest_bump(self) -> None:
        every = _dep("a", patch="1.2.9", minor="1.5.0", major="2.0.0")
        patch_only = _dep("b", patch="1.2.9")
        self.assertEqual(ProjectController._best(every, "all"), "2.0.0")
        self.assertEqual(ProjectController._best(patch_only, "all"), "1.2.9")


# ── Update All confirmation ──────────────────────────────────────────────────

class TestRequestUpdateAll(unittest.TestCase):
    def setUp(self) -> None:
        self.project = ProjectController(AppSettings(), VersionCache())
        self.project._deps = [
            _dep("a", patch="1.2.9", minor="1.5.0"),
            _dep("b", minor="1.5.0", major="2.0.0"),
            _dep("c", patch="1.2.4"),
        ]
        self.confirmed: list[tuple] = []
        self.info: list[tuple] = []
        self.project.confirmUpdateAll.connect(lambda *args: self.confirmed.append(args))
        self.project.infoMessage.connect(lambda *args: self.info.append(args))

    def test_patch_mode_counts_only_patch_updates(self) -> None:
        self.project.requestUpdateAll("patch")
        self.assertEqual(self.confirmed, [(2, "Patch only", "patch")])

    def test_patch_minor_mode(self) -> None:
        self.project.requestUpdateAll("patch_minor")
        self.assertEqual(self.confirmed, [(3, "Patch & Minor only", "patch_minor")])

    def test_all_mode(self) -> None:
        self.project.requestUpdateAll("all")
        self.assertEqual(self.confirmed, [(3, "All (including Major)", "all")])

    def test_patch_mode_without_patches_has_nothing_to_update(self) -> None:
        self.project._deps = [_dep("b", minor="1.5.0", major="2.0.0")]
        self.project.requestUpdateAll("patch")
        self.assertEqual(self.confirmed, [])
        self.assertEqual([title for title, _ in self.info], ["Nothing to update"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
