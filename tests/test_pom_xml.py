"""
Unit tests for core.pom_xml — parsing pom.xml files and writing updates back
with formatting preserved.

Pure stdlib (unittest); run from the repo root with:

    python -m unittest tests.test_pom_xml
    python -m unittest discover -s tests -t .
"""
from __future__ import annotations

import os
import tempfile
import unittest

from core.pom_xml import load, save

POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
        <relativePath/> <!-- lookup parent from repository -->
    </parent>

    <groupId>nl.fortytwo</groupId>
    <artifactId>demo</artifactId>
    <version>1.0.0-SNAPSHOT</version>

    <properties>
        <java.version>17</java.version>
        <guava.version>32.1.2-jre</guava.version>
        <alias.version>${guava.version}</alias.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>com.google.guava</groupId>
            <artifactId>guava</artifactId>
            <version>${guava.version}</version>
        </dependency>
        <dependency>
            <groupId>org.apache.commons</groupId>
            <artifactId>commons-lang3</artifactId>
            <version>3.13.0</version>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>nl.fortytwo</groupId>
            <artifactId>internal-module</artifactId>
            <version>${project.version}</version>
        </dependency>
        <dependency>
            <groupId>org.example</groupId>
            <artifactId>ranged</artifactId>
            <version>[1.0,2.0)</version>
        </dependency>
        <dependency>
            <groupId>org.slf4j</groupId>
            <artifactId>slf4j-api</artifactId>
            <version>2.0.9</version>
            <exclusions>
                <exclusion>
                    <groupId>org.excluded</groupId>
                    <artifactId>never-parsed</artifactId>
                </exclusion>
            </exclusions>
        </dependency>
    </dependencies>

    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>org.junit</groupId>
                <artifactId>junit-bom</artifactId>
                <version>5.10.0</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
        </dependencies>
    </dependencyManagement>

    <build>
        <plugins>
            <plugin>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.11.0</version>
                <configuration>
                    <source>${java.version}</source>
                    <target>${java.version}</target>
                </configuration>
            </plugin>
            <plugin>
                <groupId>org.jacoco</groupId>
                <artifactId>jacoco-maven-plugin</artifactId>
                <version>0.8.11</version>
                <dependencies>
                    <dependency>
                        <groupId>org.plugin-internal</groupId>
                        <artifactId>skipped</artifactId>
                        <version>1.0.0</version>
                    </dependency>
                </dependencies>
            </plugin>
        </plugins>
    </build>

    <profiles>
        <profile>
            <id>ci</id>
            <dependencies>
                <dependency>
                    <groupId>org.profile-only</groupId>
                    <artifactId>skipped-too</artifactId>
                    <version>9.9.9</version>
                </dependency>
            </dependencies>
        </profile>
    </profiles>
</project>
"""


class PomFileMixin(unittest.TestCase):
    """Gives each test an isolated temp pom.xml."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name
        self.path = os.path.join(self.dir, "pom.xml")

    def write(self, text: str) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def read(self) -> str:
        with open(self.path, encoding="utf-8") as fh:
            return fh.read()

    def dep(self, deps, name, group=None):
        found = [d for d in deps
                 if d.name == name and (group is None or d.group == group)]
        self.assertTrue(found, f"{name} not parsed")
        return found[0]


# ── parsing ────────────────────────────────────────────────────────────────

class TestLoad(PomFileMixin):
    def setUp(self) -> None:
        super().setUp()
        self.write(POM)
        self.deps = load(self.path)

    def test_groups(self) -> None:
        by_group: dict[str, list] = {}
        for d in self.deps:
            by_group.setdefault(d.group, []).append(d.name)
        self.assertEqual(sorted(by_group), ["dependencies", "dependencyManagement",
                                            "parent", "plugins"])
        self.assertIn("com.google.guava:guava", by_group["dependencies"])
        self.assertIn("org.junit:junit-bom", by_group["dependencyManagement"])
        self.assertEqual(by_group["parent"],
                         ["org.springframework.boot:spring-boot-starter-parent"])

    def test_property_version_is_resolved(self) -> None:
        guava = self.dep(self.deps, "com.google.guava:guava")
        self.assertEqual(guava.raw_constraint, "${guava.version}")
        self.assertEqual(guava.current_version, "32.1.2-jre")
        self.assertEqual(guava.property_name, "guava.version")

    def test_literal_version(self) -> None:
        lang3 = self.dep(self.deps, "org.apache.commons:commons-lang3")
        self.assertEqual(lang3.raw_constraint, "3.13.0")
        self.assertEqual(lang3.current_version, "3.13.0")
        self.assertIsNone(lang3.property_name)

    def test_managed_version_is_skipped(self) -> None:
        names = [d.name for d in self.deps]
        self.assertNotIn("org.springframework.boot:spring-boot-starter-web", names)

    def test_project_version_reference_is_skipped(self) -> None:
        names = [d.name for d in self.deps]
        self.assertNotIn("nl.fortytwo:internal-module", names)

    def test_range_is_skipped(self) -> None:
        names = [d.name for d in self.deps]
        self.assertNotIn("org.example:ranged", names)

    def test_exclusions_do_not_confuse_coordinates(self) -> None:
        slf4j = self.dep(self.deps, "org.slf4j:slf4j-api")
        self.assertEqual(slf4j.current_version, "2.0.9")
        self.assertNotIn("org.excluded:never-parsed", [d.name for d in self.deps])

    def test_plugin_without_group_id_gets_default(self) -> None:
        compiler = self.dep(self.deps, "org.apache.maven.plugins:maven-compiler-plugin")
        self.assertEqual(compiler.group, "plugins")
        self.assertEqual(compiler.current_version, "3.11.0")

    def test_plugin_internal_dependencies_are_skipped(self) -> None:
        names = [d.name for d in self.deps]
        self.assertIn("org.jacoco:jacoco-maven-plugin", names)
        self.assertNotIn("org.plugin-internal:skipped", names)

    def test_profile_dependencies_are_skipped(self) -> None:
        self.assertNotIn("org.profile-only:skipped-too", [d.name for d in self.deps])

    def test_parent_version(self) -> None:
        parent = self.dep(self.deps, "org.springframework.boot:spring-boot-starter-parent")
        self.assertEqual(parent.current_version, "3.2.0")
        self.assertIsNone(parent.property_name)

    def test_property_indirection_resolves_to_final_property(self) -> None:
        # ${alias.version} → ${guava.version} → 32.1.2-jre; an update through
        # the alias must land on guava.version, whose value is the literal.
        self.write(POM.replace("<version>3.13.0</version>",
                               "<version>${alias.version}</version>"))
        deps = load(self.path)
        lang3 = self.dep(deps, "org.apache.commons:commons-lang3")
        self.assertEqual(lang3.current_version, "32.1.2-jre")
        self.assertEqual(lang3.property_name, "guava.version")


class TestLoadEdgeCases(PomFileMixin):
    def test_commented_out_dependency_is_ignored(self) -> None:
        self.write("""<project>
            <dependencies>
                <!--
                <dependency>
                    <groupId>org.ghost</groupId>
                    <artifactId>ghost</artifactId>
                    <version>1.0</version>
                </dependency>
                -->
                <dependency>
                    <groupId>org.real</groupId>
                    <artifactId>real</artifactId>
                    <version>2.0</version>
                </dependency>
            </dependencies>
        </project>""")
        deps = load(self.path)
        self.assertEqual([d.name for d in deps], ["org.real:real"])

    def test_snapshot_version_is_kept(self) -> None:
        self.write("""<project><dependencies><dependency>
            <groupId>g</groupId><artifactId>a</artifactId>
            <version>1.2.3-SNAPSHOT</version>
        </dependency></dependencies></project>""")
        deps = load(self.path)
        self.assertEqual(deps[0].current_version, "1.2.3-SNAPSHOT")

    def test_latest_special_version_is_skipped(self) -> None:
        self.write("""<project><dependencies><dependency>
            <groupId>g</groupId><artifactId>a</artifactId>
            <version>LATEST</version>
        </dependency></dependencies></project>""")
        self.assertEqual(load(self.path), [])

    def test_unknown_property_is_skipped(self) -> None:
        self.write("""<project><dependencies><dependency>
            <groupId>g</groupId><artifactId>a</artifactId>
            <version>${missing.version}</version>
        </dependency></dependencies></project>""")
        self.assertEqual(load(self.path), [])

    def test_duplicate_coordinates_deduped(self) -> None:
        self.write("""<project>
            <properties><netty.version>4.1.100.Final</netty.version></properties>
            <dependencies>
                <dependency>
                    <groupId>io.netty</groupId>
                    <artifactId>netty-transport-native-epoll</artifactId>
                    <version>${netty.version}</version>
                    <classifier>linux-x86_64</classifier>
                </dependency>
                <dependency>
                    <groupId>io.netty</groupId>
                    <artifactId>netty-transport-native-epoll</artifactId>
                    <version>${netty.version}</version>
                    <classifier>linux-aarch_64</classifier>
                </dependency>
            </dependencies>
        </project>""")
        deps = load(self.path)
        self.assertEqual(len(deps), 1)


# ── saving ─────────────────────────────────────────────────────────────────

class TestSave(PomFileMixin):
    def setUp(self) -> None:
        super().setUp()
        self.write(POM)
        self.deps = load(self.path)

    def _find(self, name):
        return next(d for d in self.deps if d.name == name)

    def test_literal_update_replaces_only_that_version(self) -> None:
        dep = self._find("org.apache.commons:commons-lang3")
        save(self.path, [(dep, "3.14.0")])
        text = self.read()
        self.assertIn("<version>3.14.0</version>", text)
        self.assertNotIn("<version>3.13.0</version>", text)
        # everything else is untouched, byte for byte
        self.assertEqual(text, POM.replace("3.13.0", "3.14.0"))

    def test_property_update_rewrites_the_property(self) -> None:
        dep = self._find("com.google.guava:guava")
        save(self.path, [(dep, "33.0.0-jre")])
        text = self.read()
        self.assertIn("<guava.version>33.0.0-jre</guava.version>", text)
        self.assertIn("<version>${guava.version}</version>", text)

    def test_parent_update(self) -> None:
        dep = self._find("org.springframework.boot:spring-boot-starter-parent")
        save(self.path, [(dep, "3.3.1")])
        self.assertIn("<version>3.3.1</version>", self.read())

    def test_plugin_update(self) -> None:
        dep = self._find("org.apache.maven.plugins:maven-compiler-plugin")
        save(self.path, [(dep, "3.12.1")])
        self.assertIn("<version>3.12.1</version>", self.read())

    def test_multiple_updates_in_one_write(self) -> None:
        updates = [
            (self._find("org.apache.commons:commons-lang3"), "3.14.0"),
            (self._find("org.slf4j:slf4j-api"), "2.0.12"),
            (self._find("com.google.guava:guava"), "33.0.0-jre"),
        ]
        save(self.path, updates)
        text = self.read()
        self.assertIn("<version>3.14.0</version>", text)
        self.assertIn("<version>2.0.12</version>", text)
        self.assertIn("<guava.version>33.0.0-jre</guava.version>", text)

    def test_comments_and_formatting_survive(self) -> None:
        dep = self._find("org.apache.commons:commons-lang3")
        save(self.path, [(dep, "3.14.0")])
        text = self.read()
        self.assertIn("<!-- lookup parent from repository -->", text)
        self.assertIn('<?xml version="1.0" encoding="UTF-8"?>', text)

    def test_backup_is_removed_after_success(self) -> None:
        dep = self._find("org.slf4j:slf4j-api")
        save(self.path, [(dep, "2.0.12")])
        self.assertFalse(os.path.exists(self.path + ".bak"))

    def test_save_reparses_current_file_state(self) -> None:
        # An external edit between load() and save() must not be clobbered.
        dep = self._find("org.slf4j:slf4j-api")
        self.write(self.read().replace("3.13.0", "3.13.9"))
        save(self.path, [(dep, "2.0.12")])
        text = self.read()
        self.assertIn("<version>3.13.9</version>", text)
        self.assertIn("<version>2.0.12</version>", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
