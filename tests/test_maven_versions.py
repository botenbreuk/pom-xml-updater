"""
Unit tests for core.maven_versions — comparison, stability, and bump
categorisation for Maven-style version strings.

Run from the repo root with:

    python -m unittest tests.test_maven_versions
"""
from __future__ import annotations

import unittest

from core.maven_versions import (
    categorize_bump,
    compare_versions,
    is_stable,
    max_version,
    numeric_parts,
)


class TestNumericParts(unittest.TestCase):
    def test_plain_semver(self) -> None:
        self.assertEqual(numeric_parts("2.7.18"), (2, 7, 18))

    def test_short_versions_pad_with_zero(self) -> None:
        self.assertEqual(numeric_parts("31.1"), (31, 1, 0))
        self.assertEqual(numeric_parts("5"), (5, 0, 0))

    def test_qualifiers_are_ignored(self) -> None:
        self.assertEqual(numeric_parts("32.1.2-jre"), (32, 1, 2))
        self.assertEqual(numeric_parts("6.2.0.Final"), (6, 2, 0))
        self.assertEqual(numeric_parts("1.0.0-SNAPSHOT"), (1, 0, 0))

    def test_non_numeric_start_is_none(self) -> None:
        self.assertIsNone(numeric_parts("Payara"))
        self.assertIsNone(numeric_parts(""))


class TestCompare(unittest.TestCase):
    def test_numeric_order(self) -> None:
        self.assertEqual(compare_versions("2.7.17", "2.7.18"), -1)
        self.assertEqual(compare_versions("2.10.0", "2.9.9"), 1)
        self.assertEqual(compare_versions("3.0.0", "3.0.0"), 0)

    def test_missing_segments_are_zero(self) -> None:
        self.assertEqual(compare_versions("1.2", "1.2.0"), 0)
        self.assertEqual(compare_versions("1.2", "1.2.1"), -1)

    def test_qualifiers_before_release(self) -> None:
        self.assertEqual(compare_versions("5.0.0-RC1", "5.0.0"), -1)
        self.assertEqual(compare_versions("5.0.0-M1", "5.0.0-RC1"), -1)
        self.assertEqual(compare_versions("1.2.3-SNAPSHOT", "1.2.3"), -1)
        self.assertEqual(compare_versions("1.2.3-alpha", "1.2.3-beta"), -1)

    def test_sp_and_numeric_qualifiers_after_release(self) -> None:
        self.assertEqual(compare_versions("2.0.0", "2.0.0-sp1"), -1)
        self.assertEqual(compare_versions("1.0", "1.0-1"), -1)

    def test_release_style_qualifiers(self) -> None:
        # Final / RELEASE / GA rank with plain releases
        self.assertEqual(compare_versions("6.2.0.Final", "6.2.1.Final"), -1)
        self.assertEqual(compare_versions("4.3.30.RELEASE", "5.0.0"), -1)


class TestIsStable(unittest.TestCase):
    def test_stable(self) -> None:
        for v in ("2.7.18", "32.1.2-jre", "31.1-android", "6.2.0.Final",
                  "4.3.30.RELEASE", "2.0.1.GA", "20231013", "1.0-1", "9.4.53.v20231009"):
            self.assertTrue(is_stable(v), v)

    def test_unstable(self) -> None:
        for v in ("1.0.0-SNAPSHOT", "5.0.0-RC1", "6.0.0-M3", "1.2.3-alpha",
                  "2.0.0-beta-4", "7.0.0.CR2", "3.0.0-milestone.1",
                  "2.3.0-b170201.1204", "1.0.0-preview", "17-ea"):
            self.assertFalse(is_stable(v), v)


class TestCategorizeBump(unittest.TestCase):
    def test_patch_minor_major(self) -> None:
        self.assertEqual(categorize_bump("1.2.3", "1.2.4"), "patch")
        self.assertEqual(categorize_bump("1.2.3", "1.3.0"), "minor")
        self.assertEqual(categorize_bump("1.2.3", "2.0.0"), "major")

    def test_downgrades_and_equal_are_none(self) -> None:
        self.assertIsNone(categorize_bump("1.2.3", "1.2.3"))
        self.assertIsNone(categorize_bump("1.2.3", "1.2.2"))
        self.assertIsNone(categorize_bump("2.0.0", "1.9.9"))

    def test_qualifier_only_difference_is_none(self) -> None:
        self.assertIsNone(categorize_bump("33.0.0-jre", "33.0.0-android"))

    def test_maven_style_qualifiers(self) -> None:
        self.assertEqual(categorize_bump("6.2.0.Final", "6.2.7.Final"), "patch")
        self.assertEqual(categorize_bump("4.3.30.RELEASE", "5.3.39"), "major")
        self.assertEqual(categorize_bump("31.1-jre", "32.1.2-jre"), "major")

    def test_snapshot_current_can_upgrade(self) -> None:
        self.assertEqual(categorize_bump("1.2.3-SNAPSHOT", "1.2.3"), "patch")
        self.assertEqual(categorize_bump("1.2.3-SNAPSHOT", "1.3.0"), "minor")

    def test_unparseable_is_none(self) -> None:
        self.assertIsNone(categorize_bump("abc", "1.0.0"))
        self.assertIsNone(categorize_bump("1.0.0", "abc"))


class TestMaxVersion(unittest.TestCase):
    def test_none_handling(self) -> None:
        self.assertIsNone(max_version(None, None))
        self.assertEqual(max_version(None, "1.0"), "1.0")
        self.assertEqual(max_version("1.0", None), "1.0")

    def test_picks_higher(self) -> None:
        self.assertEqual(max_version("1.9.0", "1.10.0"), "1.10.0")
        self.assertEqual(max_version("2.0.0", "1.10.0"), "2.0.0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
