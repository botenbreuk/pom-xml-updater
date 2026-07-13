"""
Maven version comparison, stability filtering, and bump categorisation.
No Qt dependency — pure Python.

Implements a pragmatic subset of Maven's ComparableVersion ordering: leading
numeric segments compare numerically, trailing qualifiers compare by a rank
table (alpha < beta < milestone < rc/cr < SNAPSHOT < release < sp), and
unknown qualifiers (Final, RELEASE, GA, jre, android, …) rank as releases.
"""
from __future__ import annotations

import re
from typing import Optional

# ── tokenising ───────────────────────────────────────────────────────────────

_SPLIT_RE = re.compile(r"[.\-_]")
_QUAL_RE = re.compile(r"([a-z]+)(\d*)")

# Rank of well-known qualifiers relative to a plain release (rank 6).
_QUALIFIER_RANK = {
    "dev": 0,
    "alpha": 1,
    "beta": 2,
    "m": 3, "milestone": 3, "ea": 3, "preview": 3,
    "rc": 4, "cr": 4,
    "snapshot": 5,
    "": 6, "final": 6, "ga": 6, "release": 6,
    "sp": 7,
}
_RELEASE_KEY = (6, 0, "")


def _tokenize(version: str) -> tuple[list[int], list[str]]:
    """Split a version into (leading numeric segments, trailing qualifier tokens)."""
    nums: list[int] = []
    quals: list[str] = []
    for token in _SPLIT_RE.split(version.strip().lower()):
        if not token:
            continue
        if token.isdigit() and not quals:
            nums.append(int(token))
        else:
            quals.append(token)
    return nums, quals


def numeric_parts(version: str) -> Optional[tuple[int, int, int]]:
    """The (major, minor, patch) numeric prefix, zero-padded; None if non-numeric."""
    nums, _ = _tokenize(version)
    if not nums:
        return None
    padded = nums + [0, 0, 0]
    return padded[0], padded[1], padded[2]


def _qual_key(qual: str) -> tuple:
    if qual.isdigit():
        # A purely numeric qualifier sorts above a release: 1.0-1 > 1.0
        return (8, int(qual), "")
    m = _QUAL_RE.match(qual)
    alpha, digits = (m.group(1), m.group(2)) if m else (qual, "")
    rank = _QUALIFIER_RANK.get(alpha, 6)
    return (rank, int(digits or 0), alpha)


def _version_key(version: str) -> tuple:
    nums, quals = _tokenize(version)
    qual_keys = [_qual_key(q) for q in quals] or [_RELEASE_KEY]
    return tuple(nums), tuple(qual_keys)


def compare_versions(a: str, b: str) -> int:
    """Return -1 / 0 / 1 for a < b / a == b / a > b."""
    a_nums, a_quals = _version_key(a)
    b_nums, b_quals = _version_key(b)

    width = max(len(a_nums), len(b_nums))
    a_padded = a_nums + (0,) * (width - len(a_nums))
    b_padded = b_nums + (0,) * (width - len(b_nums))
    if a_padded != b_padded:
        return -1 if a_padded < b_padded else 1

    depth = max(len(a_quals), len(b_quals))
    a_full = a_quals + (_RELEASE_KEY,) * (depth - len(a_quals))
    b_full = b_quals + (_RELEASE_KEY,) * (depth - len(b_quals))
    if a_full == b_full:
        return 0
    return -1 if a_full < b_full else 1


# ── stability check ──────────────────────────────────────────────────────────

_UNSTABLE_RE = re.compile(
    r"(?:^|[.\-_])(?:alpha|beta|rc|cr|milestone|ea|preview|dev|snapshot|"
    r"nightly|incubating|pre|canary|next|[bm]\d+)\d*(?:[.\-_]|$)",
    re.IGNORECASE,
)


def is_stable(version_str: str) -> bool:
    """True only for stable versions — SNAPSHOT / milestone / RC / … are rejected.

    Release-style qualifiers (Final, RELEASE, GA, sp1, jre, android, dates)
    are considered stable.
    """
    if _UNSTABLE_RE.search(version_str):
        return False
    return numeric_parts(version_str) is not None


# ── bump categorisation ──────────────────────────────────────────────────────

def categorize_bump(current: str, candidate: str) -> Optional[str]:
    """
    Compare two version strings.
    Returns 'patch', 'minor', 'major', or None (not an upgrade / parse error).
    """
    cur = numeric_parts(current)
    cand = numeric_parts(candidate)
    if cur is None or cand is None:
        return None
    if compare_versions(candidate, current) <= 0:
        return None
    if cand[0] > cur[0]:
        return "major"
    if cand[1] > cur[1]:
        return "minor"
    if cand[2] > cur[2]:
        return "patch"
    # Same numeric version: the stable release of a pre-release current
    # (1.2.3-SNAPSHOT → 1.2.3) is a patch; stable variants of a stable
    # current (33.0.0-jre vs 33.0.0-android) are not offered.
    if not is_stable(current):
        return "patch"
    return None


def max_version(a: Optional[str], b: Optional[str]) -> Optional[str]:
    """Return the higher of two version strings (either may be None)."""
    if a is None:
        return b
    if b is None:
        return a
    return b if compare_versions(b, a) > 0 else a
