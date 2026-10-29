"""
Tests for the persisted dependency-table column widths: the ``column_widths``
map on AppSettings and the AppController API the table seeds from and saves to.

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
from core.version_cache import VersionCache
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
