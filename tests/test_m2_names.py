"""
Tests for showing dependency names from the local Maven repository:
``core.m2_repo.artifact_pom_name`` and the ``displayName`` role, which falls
back to the ``groupId:artifactId`` coordinates.

Run from the repo root with:

    python -m unittest tests.test_m2_names
"""
from __future__ import annotations

import os
import tempfile
import unittest

from PyQt6.QtCore import QCoreApplication

from app.dependency_model import ROLE, DependencyModel
from core.m2_repo import artifact_pom_name
from models.dependency import DependencyInfo

_app = QCoreApplication.instance() or QCoreApplication([])

_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <parent><groupId>org.example</groupId><artifactId>parent</artifactId><version>1</version></parent>
  <artifactId>{artifact}</artifactId>
  {name}
  <organization><name>Example Org</name></organization>
  <developers><developer><name>Jane Doe</name></developer></developers>
  <properties><module.title>Widgets</module.title></properties>
</project>
"""


class LocalRepoMixin(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = tmp.name

    def install(self, version: str, name_xml: str = "", pom: str | None = None,
                coordinate: str = "org.example:widgets") -> None:
        group_id, artifact_id = coordinate.split(":")
        version_dir = os.path.join(self.repo, *group_id.split("."), artifact_id, version)
        os.makedirs(version_dir)
        text = pom if pom is not None else _POM.format(artifact=artifact_id, name=name_xml)
        with open(os.path.join(version_dir, f"{artifact_id}-{version}.pom"), "w",
                  encoding="utf-8") as f:
            f.write(text)

    def name_of(self, version: str, coordinate: str = "org.example:widgets") -> str | None:
        return artifact_pom_name(coordinate, version, repo_dir=self.repo)


# ── reading <name> ───────────────────────────────────────────────────────────

class TestPomName(LocalRepoMixin):
    def test_project_name_is_read_not_nested_names(self) -> None:
        self.install("1.0", "<name>Example Widgets</name>")
        self.assertEqual(self.name_of("1.0"), "Example Widgets")

    def test_whitespace_is_collapsed(self) -> None:
        self.install("1.0", "<name>\n    Example\n    Widgets  </name>")
        self.assertEqual(self.name_of("1.0"), "Example Widgets")

    def test_pom_without_namespace(self) -> None:
        self.install("1.0", pom="<project><artifactId>widgets</artifactId>"
                                "<name>Plain Widgets</name></project>")
        self.assertEqual(self.name_of("1.0"), "Plain Widgets")

    def test_coordinate_references_are_filled_in(self) -> None:
        self.install("1.0", "<name>${project.groupId}:${project.artifactId}</name>")
        self.assertEqual(self.name_of("1.0"), "org.example:widgets")

    def test_own_properties_are_filled_in(self) -> None:
        self.install("1.0", "<name>${module.title} Core</name>")
        self.assertEqual(self.name_of("1.0"), "Widgets Core")

    def test_unresolvable_reference_gives_no_name(self) -> None:
        self.install("1.0", "<name>${project.parent.name}</name>")
        self.assertIsNone(self.name_of("1.0"))

    def test_missing_or_blank_name_gives_no_name(self) -> None:
        self.install("1.0")
        self.install("2.0", "<name>  </name>")
        self.assertIsNone(self.name_of("1.0"))
        self.assertIsNone(self.name_of("2.0"))


# ── which POM is read ────────────────────────────────────────────────────────

class TestPomChoice(LocalRepoMixin):
    def test_version_in_use_wins(self) -> None:
        self.install("1.0", "<name>Current Name</name>")
        self.install("2.0", "<name>Newer Name</name>")
        self.assertEqual(self.name_of("1.0"), "Current Name")

    def test_newest_downloaded_version_when_in_use_is_missing(self) -> None:
        self.install("1.9", "<name>Older Name</name>")
        self.install("1.10", "<name>Newest Name</name>")
        self.assertEqual(self.name_of("2.0"), "Newest Name")

    def test_nothing_downloaded(self) -> None:
        self.assertIsNone(self.name_of("1.0"))

    def test_malformed_pom(self) -> None:
        self.install("1.0", pom="<project><name>Broken</project>")
        self.assertIsNone(self.name_of("1.0"))

    def test_invalid_coordinate(self) -> None:
        self.assertIsNone(self.name_of("1.0", coordinate="not-a-coordinate"))


# ── table role ───────────────────────────────────────────────────────────────

class TestDisplayNameRole(unittest.TestCase):
    def test_pom_name_or_coordinates(self) -> None:
        named = DependencyInfo("org.example:widgets", "dependencies", "1.0", "1.0",
                               pom_name="Example Widgets")
        unnamed = DependencyInfo("org.example:gadgets", "dependencies", "1.0", "1.0")
        model = DependencyModel()
        model.set_deps([named, unnamed])
        display = [model.data(model.index(row, 0), ROLE["displayName"]) for row in range(2)]
        self.assertEqual(display, ["Example Widgets", "org.example:gadgets"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
