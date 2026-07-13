"""
Tests for the AppController API backing the Settings › Build Tools panel —
the global default and the per-folder override list/removal.

Storage is isolated to a temp config dir; a QCoreApplication is created so the
controller's Qt machinery works headlessly.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from PyQt6.QtCore import QCoreApplication

from models.settings import AppSettings
from core.version_cache import VersionCache
from app.app_controller import AppController

_app = QCoreApplication.instance() or QCoreApplication([])


class AppControllerBuildToolTest(unittest.TestCase):
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

        self.settings = AppSettings(); self.settings.load()
        self.appc = AppController(self.settings, VersionCache())
        self.addCleanup(self.appc.shutdown)

    def test_default_defaults_to_mvn(self) -> None:
        self.assertEqual(self.appc.defaultBuildTool, "mvn")

    def test_set_default_persists_and_signals(self) -> None:
        spy: list[int] = []
        self.appc.toolSettingsChanged.connect(lambda: spy.append(1))
        self.appc.setDefaultBuildTool("mvnd")
        self.assertEqual(self.appc.defaultBuildTool, "mvnd")
        self.assertEqual(len(spy), 1)
        reloaded = AppSettings(); reloaded.load()
        self.assertEqual(reloaded.default_build_tool, "mvnd")

    def test_set_default_invalid_is_noop(self) -> None:
        self.appc.setDefaultBuildTool("gradle")
        self.assertEqual(self.appc.defaultBuildTool, "mvn")

    def test_overrides_list_is_sorted_with_display_names(self) -> None:
        self.settings.build_tool_overrides = {"/z/proj": "mvnw", "/a/proj": "mvnd"}
        ov = self.appc.buildToolOverrides
        self.assertEqual([o["path"] for o in ov], ["/a/proj", "/z/proj"])
        self.assertEqual(ov[0], {"path": "/a/proj", "tool": "mvnd", "name": "Maven Daemon"})
        self.assertEqual(ov[1]["name"], "Maven Wrapper")

    def test_remove_override(self) -> None:
        self.settings.set_build_tool_override("/a", "mvnw")
        self.appc.removeBuildToolOverride("/a")
        self.assertEqual(self.appc.buildToolOverrides, [])
        reloaded = AppSettings(); reloaded.load()
        self.assertEqual(reloaded.build_tool_overrides, {})

    def test_picker_pin_refreshes_overrides_list(self) -> None:
        # A per-folder pin made through the picker (BuildTool.choose) must
        # refresh the Settings panel — BuildTool and App share the settings
        # object, but App still needs its notify to fire.  main.py wires
        # overridesChanged -> toolSettingsChanged.
        from app.build_tool_controller import BuildToolController
        bt = BuildToolController(self.settings)
        bt.overridesChanged.connect(self.appc.toolSettingsChanged)
        spy: list[int] = []
        self.appc.toolSettingsChanged.connect(lambda: spy.append(1))

        bt.setProject("/tmp/demo-proj")
        bt.choose("mvnd", True)

        self.assertTrue(spy, "toolSettingsChanged should fire so the panel re-reads the list")
        self.assertEqual(self.appc.buildToolOverrides,
                         [{"path": "/tmp/demo-proj", "tool": "mvnd", "name": "Maven Daemon"}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
