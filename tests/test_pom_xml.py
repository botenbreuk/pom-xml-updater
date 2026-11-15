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
from xml.parsers.expat import ExpatError

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

    def write_bytes(self, data: bytes) -> None:
        with open(self.path, "wb") as fh:
            fh.write(data)

    def read_bytes(self) -> bytes:
        with open(self.path, "rb") as fh:
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

    def test_property_named_like_a_pom_tag_is_not_that_tag(self) -> None:
        # "-" and "." don't end a tag name: <dependency-check-maven.version> is
        # not a <dependency>.  Each property below used to open a phantom
        # element that ran on to the tag's next real closing tag, swallowing
        # or hiding entries.  The parent sits after <properties> so a phantom
        # section starting there would cover it.
        pom = """<project>
            <properties>
                <PROP>1.0</PROP>
                <lib.version>2.0</lib.version>
            </properties>
            <parent>
                <groupId>org.p</groupId><artifactId>parent</artifactId>
                <version>3.0</version>
            </parent>
            <dependencyManagement><dependencies><dependency>
                <groupId>org.m</groupId><artifactId>bom</artifactId>
                <version>${lib.version}</version>
            </dependency></dependencies></dependencyManagement>
            <dependencies><dependency>
                <groupId>org.d</groupId><artifactId>lib</artifactId>
                <version>${lib.version}</version>
            </dependency></dependencies>
            <build><plugins><plugin>
                <groupId>org.b</groupId><artifactId>build-plugin</artifactId>
                <version>4.0</version>
            </plugin></plugins></build>
            <reporting><plugins><plugin>
                <groupId>org.r</groupId><artifactId>report-plugin</artifactId>
                <version>5.0</version>
            </plugin></plugins></reporting>
            <profiles><profile><id>ci</id></profile></profiles>
        </project>"""
        expected = [
            ("dependencyManagement", "org.m:bom"),
            ("dependencies", "org.d:lib"),
            ("plugins", "org.b:build-plugin"),
            ("plugins", "org.r:report-plugin"),
            ("parent", "org.p:parent"),
        ]
        for prop in ("dependency-check-maven.version", "dependencyManagement.note",
                     "plugin.version", "build.timestamp", "reporting.note",
                     "profiles.active"):
            with self.subTest(prop=prop):
                self.write(pom.replace("PROP", prop))
                self.assertEqual([(d.group, d.name) for d in load(self.path)], expected)

    def test_child_elements_in_any_order(self) -> None:
        # Maven accepts a pom's child elements in any order, so <version> can
        # come after <exclusions> or <configuration>.
        self.write("""<project>
            <dependencies><dependency>
                <groupId>org.slf4j</groupId><artifactId>slf4j-api</artifactId>
                <exclusions><exclusion>
                    <groupId>org.excluded</groupId><artifactId>never-parsed</artifactId>
                </exclusion></exclusions>
                <version>2.0.9</version>
            </dependency></dependencies>
            <build><plugins><plugin>
                <artifactId>maven-surefire-plugin</artifactId>
                <configuration><skipTests>true</skipTests></configuration>
                <version>3.2.5</version>
            </plugin></plugins></build>
        </project>""")
        self.assertEqual([(d.name, d.current_version) for d in load(self.path)], [
            ("org.slf4j:slf4j-api", "2.0.9"),
            ("org.apache.maven.plugins:maven-surefire-plugin", "3.2.5"),
        ])

    def test_plugins_nested_in_a_plugin_configuration_are_skipped(self) -> None:
        # maven-site-plugin's <reportPlugins> holds <plugin> elements of its
        # own.  The first one's </plugin> used to end the outer plugin, so the
        # second one and the outer plugin's own dependency were listed.
        self.write("""<project><build><plugins><plugin>
            <artifactId>maven-site-plugin</artifactId>
            <version>3.12.1</version>
            <configuration><reportPlugins>
                <plugin>
                    <artifactId>maven-jxr-plugin</artifactId><version>3.3.0</version>
                </plugin>
                <plugin>
                    <artifactId>maven-javadoc-plugin</artifactId><version>3.6.0</version>
                </plugin>
            </reportPlugins></configuration>
            <dependencies><dependency>
                <groupId>org.apache.maven.doxia</groupId>
                <artifactId>doxia-module-markdown</artifactId>
                <version>1.12.0</version>
            </dependency></dependencies>
        </plugin></plugins></build></project>""")
        self.assertEqual([(d.group, d.name) for d in load(self.path)],
                         [("plugins", "org.apache.maven.plugins:maven-site-plugin")])

    def test_developer_properties_are_not_the_project_properties(self) -> None:
        # A <developer> can have <properties> too, and <developers> comes
        # first in the usual element order.  Those used to be taken for the
        # project's, which left every ${...} version unresolved.
        self.write("""<project>
            <developers><developer>
                <id>jdoe</id>
                <properties><picUrl>https://example.org/jdoe.png</picUrl></properties>
            </developer></developers>
            <properties><guava.version>32.1.2-jre</guava.version></properties>
            <dependencies><dependency>
                <groupId>com.google.guava</groupId><artifactId>guava</artifactId>
                <version>${guava.version}</version>
            </dependency></dependencies>
        </project>""")
        guava = self.dep(load(self.path), "com.google.guava:guava")
        self.assertEqual(guava.current_version, "32.1.2-jre")

    def test_profiles_tag_in_a_plugin_configuration_does_not_end_profiles(self) -> None:
        # A plugin can be configured with a <profiles> element of its own.
        # Inside a profile, it used to end <profiles>, so the plugins of the
        # profiles after it were listed.
        self.write("""<project><profiles>
            <profile><id>a</id><build><plugins><plugin>
                <artifactId>maven-gpg-plugin</artifactId><version>3.2.8</version>
                <configuration><profiles>keep</profiles></configuration>
            </plugin></plugins></build></profile>
            <profile><id>b</id><build><plugins><plugin>
                <artifactId>maven-deploy-plugin</artifactId><version>3.1.1</version>
            </plugin></plugins></build></profile>
        </profiles></project>""")
        self.assertEqual(load(self.path), [])

    def test_xhtml_entity_in_a_developer_name(self) -> None:
        # Maven predefines the XHTML entities, so poms do use them.
        self.write("""<project>
            <developers><developer><name>Trygve Laugst&oslash;l</name></developer></developers>
            <dependencies><dependency>
                <groupId>g</groupId><artifactId>a</artifactId><version>1.0</version>
            </dependency></dependencies>
        </project>""")
        self.assertEqual([d.name for d in load(self.path)], ["g:a"])

    def test_version_not_written_as_plain_text_is_skipped(self) -> None:
        # save() replaces the version's bytes in the file, and these aren't "1.0".
        for version in ("1&#46;0", "1.<!-- split -->0"):
            with self.subTest(version=version):
                self.write(f"""<project><dependencies><dependency>
                    <groupId>g</groupId><artifactId>a</artifactId>
                    <version>{version}</version>
                </dependency></dependencies></project>""")
                self.assertEqual(load(self.path), [])

    def test_malformed_or_non_pom_file_raises(self) -> None:
        for text, error in (("<project><dependencies></project>", ExpatError),
                            ("<settings><dependencies/></settings>", ValueError)):
            with self.subTest(text=text):
                self.write(text)
                with self.assertRaises(error):
                    load(self.path)


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


class TestSaveKeepsBytes(PomFileMixin):
    """save() changes only the version's bytes, whatever else is in the file."""

    def update(self, original: bytes) -> bytes:
        self.write_bytes(original)
        save(self.path, [(load(self.path)[0], "2.0")])
        return self.read_bytes()

    def test_crlf_line_endings(self) -> None:
        original = (b"<project>\r\n"
                    b"    <dependencies><dependency>\r\n"
                    b"        <groupId>g</groupId><artifactId>a</artifactId>\r\n"
                    b"        <version>1.0</version>\r\n"
                    b"    </dependency></dependencies>\r\n"
                    b"</project>\r\n")
        self.assertEqual(self.update(original), original.replace(b"1.0", b"2.0"))

    def test_encodings(self) -> None:
        pom = ('<?xml version="1.0" encoding="{}"?>\n'
               "<project><name>Café</name><dependencies><dependency>"
               "<groupId>g</groupId><artifactId>a</artifactId><version>1.0</version>"
               "</dependency></dependencies></project>\n")
        for name, original in (
                ("ISO-8859-1", pom.format("ISO-8859-1").encode("latin-1")),
                ("UTF-8 with BOM", pom.format("UTF-8").encode("utf-8-sig"))):
            with self.subTest(name):
                self.assertEqual(self.update(original),
                                 original.replace(b">1.0<", b">2.0<"))

    def test_comment_beside_the_version(self) -> None:
        original = (b"<project><dependencies><dependency>"
                    b"<groupId>g</groupId><artifactId>a</artifactId>"
                    b"<version>1.0<!-- pinned: see #12 --></version>"
                    b"</dependency></dependencies></project>\n")
        self.assertEqual(self.update(original), original.replace(b"1.0", b"2.0"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
