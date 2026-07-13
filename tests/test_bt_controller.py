"""
Tests for the BuildToolController (QML `BuildTool`) — resolution on project
open, applying a choice, persisting a per-folder pin, and reporting the
detected tools.

Signals are delivered synchronously to Python slots (direct connections), so a
QCoreApplication is enough — no event loop needed.  Storage is isolated to a
temp config dir so nothing touches the developer's real settings.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from PyQt6.QtCore import QCoreApplication

from models.settings import AppSettings
from app.build_tool_controller import BuildToolController

_app = QCoreApplication.instance() or QCoreApplication([])


class BuildToolControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        proj = tempfile.TemporaryDirectory(); self.addCleanup(proj.cleanup)
        cfg = tempfile.TemporaryDirectory();  self.addCleanup(cfg.cleanup)
        self.proj = proj.name

        backup = {v: os.environ.get(v) for v in ("XDG_CONFIG_HOME", "APPDATA")}
        for v in backup:
            os.environ[v] = cfg.name

        def restore() -> None:
            for v, val in backup.items():
                if val is None:
                    os.environ.pop(v, None)
                else:
                    os.environ[v] = val

        self.addCleanup(restore)

    def touch(self, name: str) -> None:
        with open(os.path.join(self.proj, name), "w"):
            pass

    # ── resolution ─────────────────────────────────────────────────────────

    def test_wrapper_project_resolves_without_prompt(self) -> None:
        self.touch("mvnw")
        bt = BuildToolController(AppSettings())
        seen: list[str] = []
        bt.showPicker.connect(lambda cid: seen.append(cid))
        bt.setProject(self.proj)
        self.assertEqual(seen, [])
        self.assertEqual(bt.activeId, "mvnw")
        self.assertEqual(bt.installCommand, "mvnw dependency:resolve")
        self.assertEqual(bt.projectDir, self.proj)

    def test_plain_project_uses_default(self) -> None:
        bt = BuildToolController(AppSettings())
        bt.setProject(self.proj)
        self.assertEqual(bt.activeId, "mvn")
        self.assertEqual(bt.installCommand, "mvn dependency:resolve")

    def test_request_picker_emits_current_id(self) -> None:
        bt = BuildToolController(AppSettings())
        seen: list[str] = []
        bt.showPicker.connect(lambda cid: seen.append(cid))
        bt.requestPicker()
        self.assertEqual(seen, ["mvn"])

    # ── choosing ───────────────────────────────────────────────────────────

    def test_choose_remember_persists_and_wins_next_open(self) -> None:
        self.touch("mvnw")
        settings = AppSettings()
        bt = BuildToolController(settings)
        bt.setProject(self.proj)
        changed: list[str] = []
        bt.activeChanged.connect(lambda: changed.append(bt.activeId))

        bt.choose("mvnd", True)
        self.assertEqual(bt.activeId, "mvnd")
        self.assertEqual(bt.installCommand, "mvnd dependency:resolve")
        self.assertTrue(bt.hasOverride)
        self.assertTrue(changed)

        # a fresh controller over the reloaded settings resolves straight to mvnd
        reloaded = AppSettings(); reloaded.load()
        bt2 = BuildToolController(reloaded)
        bt2.setProject(self.proj)
        self.assertEqual(bt2.activeId, "mvnd")

    def test_choose_one_off_does_not_persist(self) -> None:
        self.touch("mvnw")
        settings = AppSettings()
        bt = BuildToolController(settings)
        bt.setProject(self.proj)
        bt.choose("mvn", False)
        self.assertEqual(bt.activeId, "mvn")
        self.assertFalse(bt.hasOverride)
        self.assertIsNone(settings.build_tool_override(self.proj))

    def test_invalid_choice_is_ignored(self) -> None:
        self.touch("mvnw")
        bt = BuildToolController(AppSettings())
        bt.setProject(self.proj)
        bt.choose("gradle", True)
        self.assertEqual(bt.activeId, "mvnw")   # unchanged

    def test_reevaluate_follows_settings_change(self) -> None:
        settings = AppSettings()
        bt = BuildToolController(settings)
        bt.setProject(self.proj)
        self.assertEqual(bt.activeId, "mvn")
        settings.default_build_tool = "mvnd"
        bt.reevaluate()
        self.assertEqual(bt.activeId, "mvnd")

    # ── introspection ──────────────────────────────────────────────────────

    def test_detected_tools_reports_wrapper(self) -> None:
        self.touch("mvnw")
        bt = BuildToolController(AppSettings())
        bt.setProject(self.proj)
        self.assertEqual(bt.detectedTools().get("mvnw"), "mvnw")

    def test_detected_tools_without_project_has_no_wrapper(self) -> None:
        bt = BuildToolController(AppSettings())
        self.assertNotIn("mvnw", bt.detectedTools())


if __name__ == "__main__":
    unittest.main(verbosity=2)
