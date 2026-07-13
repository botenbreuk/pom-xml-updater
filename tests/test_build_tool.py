"""
Unit tests for core.build_tool — the build-tool abstraction and detection.

Pure stdlib (unittest); run from the repo root with:

    python -m unittest tests.test_build_tool
    python -m unittest discover -s tests -t .
"""
from __future__ import annotations

import os
import tempfile
import unittest

from core.build_tool import (
    DEFAULT_TOOL,
    Detection,
    DetectionSource,
    BuildTool,
    detect,
    find_wrapper_dir,
    wrapper_script_path,
)

MAVEN = BuildTool.MAVEN
WRAPPER = BuildTool.WRAPPER
MVND = BuildTool.MVND


class ProjectDirMixin(unittest.TestCase):
    """Gives each test an isolated temp project directory."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def touch(self, name: str, *, in_dir: str | None = None) -> None:
        path = os.path.join(in_dir or self.dir, name)
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8"):
            pass

    def subdir(self, *parts: str) -> str:
        path = os.path.join(self.dir, *parts)
        os.makedirs(path, exist_ok=True)
        return path


# ── metadata & command builders ───────────────────────────────────────────

class TestMetadata(unittest.TestCase):
    def test_ids_and_display(self) -> None:
        self.assertEqual(MAVEN.id, "mvn")
        self.assertEqual(WRAPPER.id, "mvnw")
        self.assertEqual(MVND.id, "mvnd")
        self.assertEqual((MAVEN.display, WRAPPER.display, MVND.display),
                         ("Maven", "Maven Wrapper", "Maven Daemon"))

    def test_enum_order_is_mvn_first(self) -> None:
        self.assertEqual(list(BuildTool), [MAVEN, WRAPPER, MVND])

    def test_default_tool_is_maven(self) -> None:
        self.assertIs(DEFAULT_TOOL, MAVEN)


class TestFromId(unittest.TestCase):
    def test_known_ids(self) -> None:
        self.assertIs(BuildTool.from_id("mvn"), MAVEN)
        self.assertIs(BuildTool.from_id("mvnw"), WRAPPER)
        self.assertIs(BuildTool.from_id("mvnd"), MVND)

    def test_case_insensitive_and_whitespace(self) -> None:
        self.assertIs(BuildTool.from_id("  MVND  "), MVND)
        self.assertIs(BuildTool.from_id("Mvn"), MAVEN)

    def test_passthrough_instance(self) -> None:
        self.assertIs(BuildTool.from_id(WRAPPER), WRAPPER)

    def test_unknown_and_empty(self) -> None:
        for bad in (None, "", "   ", "gradle", "maven3", "ant"):
            self.assertIsNone(BuildTool.from_id(bad))


class TestCommandBuilders(unittest.TestCase):
    def test_install(self) -> None:
        self.assertEqual(MAVEN.install_cmd(), ["mvn", "dependency:resolve"])
        self.assertEqual(WRAPPER.install_cmd(), ["mvnw", "dependency:resolve"])
        self.assertEqual(MVND.install_cmd(), ["mvnd", "dependency:resolve"])

    def test_clean_install_forces_updates(self) -> None:
        self.assertEqual(MAVEN.clean_install_cmd(), ["mvn", "-U", "dependency:resolve"])

    def test_version(self) -> None:
        for tool in BuildTool:
            self.assertEqual(tool.version_cmd(), [tool.binary, "--version"])

    def test_get_with_version(self) -> None:
        self.assertEqual(
            MAVEN.get_cmd("com.google.guava:guava", "33.0.0-jre"),
            ["mvn", "dependency:get", "-Dartifact=com.google.guava:guava:33.0.0-jre"])

    def test_get_without_version(self) -> None:
        self.assertEqual(MVND.get_cmd("org.slf4j:slf4j-api"),
                         ["mvnd", "dependency:get", "-Dartifact=org.slf4j:slf4j-api"])


# ── detection ──────────────────────────────────────────────────────────────

class TestDetect(ProjectDirMixin):
    def test_wrapper_script_resolves(self) -> None:
        self.touch("mvnw")
        result = detect(self.dir)
        self.assertEqual(result.tool, WRAPPER)
        self.assertEqual(result.source, DetectionSource.WRAPPER_SCRIPT)
        self.assertEqual(result.wrapper_dir, os.path.abspath(self.dir))

    def test_windows_wrapper_script_resolves(self) -> None:
        self.touch("mvnw.cmd")
        result = detect(self.dir)
        self.assertEqual(result.tool, WRAPPER)

    def test_override_beats_wrapper(self) -> None:
        self.touch("mvnw")
        result = detect(self.dir, override="mvnd")
        self.assertEqual(result.tool, MVND)
        self.assertEqual(result.source, DetectionSource.OVERRIDE)
        # the wrapper location is still reported for informational use
        self.assertEqual(result.wrapper_dir, os.path.abspath(self.dir))

    def test_override_accepts_instance(self) -> None:
        result = detect(self.dir, override=MVND)
        self.assertEqual(result.tool, MVND)
        self.assertEqual(result.source, DetectionSource.OVERRIDE)

    def test_unknown_override_is_ignored(self) -> None:
        self.touch("mvnw")
        result = detect(self.dir, override="gradle")
        self.assertEqual(result.tool, WRAPPER)
        self.assertEqual(result.source, DetectionSource.WRAPPER_SCRIPT)

    def test_nothing_found_defaults_to_maven(self) -> None:
        result = detect(self.dir)
        self.assertEqual(result.tool, MAVEN)
        self.assertEqual(result.source, DetectionSource.DEFAULT)
        self.assertIsNone(result.wrapper_dir)

    def test_custom_default_is_respected(self) -> None:
        result = detect(self.dir, default="mvnd")
        self.assertEqual(result.tool, MVND)
        self.assertEqual(result.source, DetectionSource.DEFAULT)

    def test_bad_default_falls_back_to_maven(self) -> None:
        self.assertEqual(detect(self.dir, default="nonsense").tool, MAVEN)

    def test_empty_project_dir_defaults(self) -> None:
        result = detect("", default="mvnd")
        self.assertEqual(result.tool, MVND)
        self.assertEqual(result.source, DetectionSource.DEFAULT)

    def test_empty_project_dir_still_honors_override(self) -> None:
        result = detect("", override="mvnw")
        self.assertEqual(result.tool, WRAPPER)
        self.assertEqual(result.source, DetectionSource.OVERRIDE)


class TestDetectMultiModule(ProjectDirMixin):
    def test_wrapper_found_in_parent(self) -> None:
        self.touch("mvnw")                                # repo root == self.dir
        module = self.subdir("modules", "api")            # nested module
        result = detect(module)
        self.assertEqual(result.tool, WRAPPER)
        self.assertEqual(result.wrapper_dir, os.path.abspath(self.dir))

    def test_nearest_wrapper_wins(self) -> None:
        self.touch("mvnw")
        module = self.subdir("modules", "api")
        self.touch("mvnw", in_dir=module)
        self.assertEqual(find_wrapper_dir(module), os.path.abspath(module))

    def test_wrapper_script_path_prefers_platform_script(self) -> None:
        self.touch("mvnw")
        path = wrapper_script_path(self.dir)
        self.assertIsNotNone(path)
        self.assertTrue(path.endswith("mvnw") or path.endswith("mvnw.cmd"))

    def test_wrapper_script_path_none_without_wrapper(self) -> None:
        self.assertIsNone(wrapper_script_path(self.dir))


class TestDetectRobustness(ProjectDirMixin):
    def test_nonexistent_directory_defaults(self) -> None:
        missing = os.path.join(self.dir, "does", "not", "exist")
        result = detect(missing)
        self.assertEqual(result.tool, MAVEN)
        self.assertEqual(result.source, DetectionSource.DEFAULT)

    def test_mvnw_directory_is_not_a_script(self) -> None:
        os.makedirs(os.path.join(self.dir, "mvnw"))
        result = detect(self.dir)
        self.assertEqual(result.source, DetectionSource.DEFAULT)

    def test_detection_result_is_frozen(self) -> None:
        result = detect(self.dir)
        self.assertIsInstance(result, Detection)
        with self.assertRaises(Exception):
            result.tool = MVND  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main(verbosity=2)
