"""
Round-trip tests for the build-tool settings: ``default_build_tool`` and the
per-directory ``build_tool_overrides`` map on AppSettings.

Isolated from the user's real settings by pointing the config directory at a
temp dir via XDG_CONFIG_HOME / APPDATA before each test, so nothing here can
read or clobber the developer's own settings.ini.

Run from the repo root with:

    python -m unittest tests.test_settings_build_tool
"""
from __future__ import annotations

import os
import tempfile
import unittest

from models.settings import AppSettings


class SettingsIsolationMixin(unittest.TestCase):
    """Redirects AppSettings' storage to a throwaway directory per test."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.config_dir = tmp.name

        backup = {var: os.environ.get(var) for var in ("XDG_CONFIG_HOME", "APPDATA")}
        for var in backup:
            os.environ[var] = self.config_dir

        def restore() -> None:
            for var, val in backup.items():
                if val is None:
                    os.environ.pop(var, None)
                else:
                    os.environ[var] = val

        self.addCleanup(restore)

    @staticmethod
    def fresh_loaded() -> AppSettings:
        """A brand-new AppSettings populated from whatever is on disk."""
        s = AppSettings()
        s.load()
        return s


# ── defaults ───────────────────────────────────────────────────────────────

class TestDefaults(SettingsIsolationMixin):
    def test_field_defaults(self) -> None:
        s = AppSettings()
        self.assertEqual(s.default_build_tool, "mvn")
        self.assertEqual(s.build_tool_overrides, {})

    def test_load_with_empty_store_gives_defaults(self) -> None:
        s = self.fresh_loaded()
        self.assertEqual(s.default_build_tool, "mvn")
        self.assertEqual(s.build_tool_overrides, {})


# ── round-trips ──────────────────────────────────────────────────────────────

class TestRoundTrip(SettingsIsolationMixin):
    def test_default_tool_persists(self) -> None:
        s = AppSettings()
        s.default_build_tool = "mvnd"
        s.save()
        self.assertEqual(self.fresh_loaded().default_build_tool, "mvnd")

    def test_overrides_persist(self) -> None:
        s = AppSettings()
        s.build_tool_overrides = {
            "/Users/me/proj-a": "mvnd",
            "/Users/me/proj-b": "mvnw",
        }
        s.save()
        self.assertEqual(
            self.fresh_loaded().build_tool_overrides,
            {"/Users/me/proj-a": "mvnd", "/Users/me/proj-b": "mvnw"},
        )

    def test_new_keys_do_not_disturb_existing_settings(self) -> None:
        s = AppSettings()
        s.min_age_days = 7
        s.theme = "dark"
        s.default_build_tool = "mvnw"
        s.save()
        loaded = self.fresh_loaded()
        self.assertEqual(loaded.min_age_days, 7)
        self.assertEqual(loaded.theme, "dark")
        self.assertEqual(loaded.default_build_tool, "mvnw")


# ── override helpers ─────────────────────────────────────────────────────────

class TestOverrideHelpers(SettingsIsolationMixin):
    def test_lookup_returns_none_when_unset(self) -> None:
        self.assertIsNone(AppSettings().build_tool_override("/some/dir"))

    def test_set_persists_immediately(self) -> None:
        s = AppSettings()
        s.set_build_tool_override("/Users/me/proj", "mvnd")
        self.assertEqual(s.build_tool_override("/Users/me/proj"), "mvnd")
        # auto-saved — a fresh load sees it without an explicit save()
        self.assertEqual(self.fresh_loaded().build_tool_override("/Users/me/proj"), "mvnd")

    def test_set_normalizes_via_from_id(self) -> None:
        s = AppSettings()
        s.set_build_tool_override("/p", "  MVND ")
        self.assertEqual(s.build_tool_override("/p"), "mvnd")

    def test_set_invalid_tool_is_noop(self) -> None:
        s = AppSettings()
        s.set_build_tool_override("/p", "gradle")
        self.assertIsNone(s.build_tool_override("/p"))
        self.assertEqual(self.fresh_loaded().build_tool_overrides, {})

    def test_set_empty_dir_is_noop(self) -> None:
        s = AppSettings()
        s.set_build_tool_override("", "mvn")
        self.assertEqual(s.build_tool_overrides, {})

    def test_clear_removes_and_persists(self) -> None:
        s = AppSettings()
        s.set_build_tool_override("/p", "mvnw")
        s.clear_build_tool_override("/p")
        self.assertIsNone(s.build_tool_override("/p"))
        self.assertEqual(self.fresh_loaded().build_tool_overrides, {})

    def test_clear_unknown_dir_is_harmless(self) -> None:
        s = AppSettings()
        s.clear_build_tool_override("/never/set")  # must not raise
        self.assertEqual(s.build_tool_overrides, {})


# ── sanitization on load ─────────────────────────────────────────────────────

class TestSanitization(SettingsIsolationMixin):
    def test_bad_default_tool_falls_back_to_mvn(self) -> None:
        s = AppSettings()
        s.default_build_tool = "gradle"   # not supported
        s.save()
        self.assertEqual(self.fresh_loaded().default_build_tool, "mvn")

    def test_default_tool_is_case_normalized(self) -> None:
        s = AppSettings()
        s.default_build_tool = "MVND"
        s.save()
        self.assertEqual(self.fresh_loaded().default_build_tool, "mvnd")

    def test_invalid_override_entries_are_dropped(self) -> None:
        s = AppSettings()
        s.build_tool_overrides = {
            "/good": "mvnd",
            "/bad": "gradle",
            "/also-bad": "",
        }
        s.save()
        self.assertEqual(self.fresh_loaded().build_tool_overrides, {"/good": "mvnd"})

    def test_override_values_are_case_normalized(self) -> None:
        s = AppSettings()
        s.build_tool_overrides = {"/p": "Mvnw"}
        s.save()
        self.assertEqual(self.fresh_loaded().build_tool_overrides, {"/p": "mvnw"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
