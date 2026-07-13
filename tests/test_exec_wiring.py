"""
Tests that the exec sites resolve and drive the active build tool instead of
hardcoding Maven.

Covers:
  * AppSettings.resolve_build_tool / active_build_tool
  * InstallController._invocation (resolve argv, per platform, incl. wrapper)
  * core.m2_repo.artifact_in_local_repo (pending-resolve detection)

Run from the repo root with:

    python -m unittest tests.test_exec_wiring
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from core.build_tool import BuildTool
from core.m2_repo import artifact_in_local_repo
from models.settings import AppSettings

MAVEN = BuildTool.MAVEN
WRAPPER = BuildTool.WRAPPER
MVND = BuildTool.MVND


class ProjectDirMixin(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name

    def touch(self, name: str) -> None:
        with open(os.path.join(self.dir, name), "w"):
            pass


# ── settings-driven resolution ────────────────────────────────────────────

class TestToolResolution(ProjectDirMixin):
    def _settings(self, *, default: str = "mvn", overrides: dict | None = None) -> AppSettings:
        # In-memory only — no save()/load(), so this never touches disk.
        s = AppSettings()
        s.default_build_tool = default
        s.build_tool_overrides = dict(overrides or {})
        return s

    def test_override_wins_over_wrapper(self) -> None:
        self.touch("mvnw")
        s = self._settings(overrides={self.dir: "mvnd"})
        self.assertEqual(s.active_build_tool(self.dir), MVND)

    def test_wrapper_script_detected(self) -> None:
        self.touch("mvnw")
        self.assertEqual(self._settings().active_build_tool(self.dir), WRAPPER)

    def test_nothing_found_uses_default(self) -> None:
        s = self._settings(default="mvnd")
        self.assertEqual(s.active_build_tool(self.dir), MVND)

    def test_resolve_exposes_wrapper_dir(self) -> None:
        self.touch("mvnw")
        result = self._settings().resolve_build_tool(self.dir)
        self.assertEqual(result.tool, WRAPPER)
        self.assertEqual(result.wrapper_dir, os.path.abspath(self.dir))


# ── resolve command construction ──────────────────────────────────────────

class TestInstallInvocation(ProjectDirMixin):
    def test_posix_uses_tool_binary_and_resolve(self) -> None:
        from app.install_controller import InstallController
        for tool in (MAVEN, MVND):
            with self.subTest(tool=tool.id):
                program, args = InstallController._invocation(
                    tool, os.environ.get("PATH", ""), self.dir)
                self.assertEqual(args, ["dependency:resolve"])
                # resolved to a full path or left as the bare binary name
                self.assertTrue(program == tool.binary
                                or os.path.basename(program) == tool.binary)

    def test_wrapper_uses_project_script(self) -> None:
        from app.install_controller import InstallController
        self.touch("mvnw")
        program, args = InstallController._invocation(WRAPPER, "", self.dir)
        self.assertEqual(program, os.path.join(os.path.abspath(self.dir), "mvnw"))
        self.assertEqual(args, ["dependency:resolve"])

    def test_windows_wraps_in_cmd(self) -> None:
        from app.install_controller import InstallController
        with mock.patch("app.install_controller.sys.platform", "win32"):
            program, args = InstallController._invocation(MVND, "", self.dir)
            self.assertEqual(program, "cmd.exe")
            self.assertEqual(args, ["/c", "mvnd", "dependency:resolve"])


# ── local-repo pending detection ───────────────────────────────────────────

class TestArtifactInLocalRepo(ProjectDirMixin):
    def _install(self, group: str, artifact: str, version: str) -> None:
        d = os.path.join(self.dir, *group.split("."), artifact, version)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{artifact}-{version}.jar"), "w"):
            pass

    def test_present_artifact_is_found(self) -> None:
        self._install("com.google.guava", "guava", "33.0.0-jre")
        self.assertTrue(artifact_in_local_repo(
            "com.google.guava:guava", "33.0.0-jre", repo_dir=self.dir))

    def test_other_version_is_not_found(self) -> None:
        self._install("com.google.guava", "guava", "32.1.2-jre")
        self.assertFalse(artifact_in_local_repo(
            "com.google.guava:guava", "33.0.0-jre", repo_dir=self.dir))

    def test_empty_version_dir_is_not_found(self) -> None:
        os.makedirs(os.path.join(self.dir, "org", "x", "a", "1.0"))
        self.assertFalse(artifact_in_local_repo("org.x:a", "1.0", repo_dir=self.dir))

    def test_invalid_coordinate_is_not_found(self) -> None:
        self.assertFalse(artifact_in_local_repo("not-a-coordinate", "1.0",
                                                repo_dir=self.dir))
        self.assertFalse(artifact_in_local_repo("g:a", "", repo_dir=self.dir))


if __name__ == "__main__":
    unittest.main(verbosity=2)
