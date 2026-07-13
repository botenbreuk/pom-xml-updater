"""
Read and update Maven pom.xml files while preserving formatting.
No Qt dependency — pure Python.

Parsing is deliberately text-based (regular expressions over the raw file)
rather than DOM-based: updates are applied as exact byte-range replacements,
so the file's formatting, comments, and element order are preserved untouched.

Sections processed:
    <dependencies>                      → group "dependencies"
    <dependencyManagement>              → group "dependencyManagement"
    <build>/<reporting> plugins         → group "plugins"  (incl. pluginManagement)
    <parent>                            → group "parent"

Entries without a resolvable version — managed by a parent/BOM, version
ranges, ``LATEST``/``RELEASE``, or ``${project.version}``-style internal
references — are skipped: there is nothing meaningful to update for them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from shutil import copy2
from typing import Optional

from models.dependency import DependencyInfo

GROUPS = ("dependencies", "dependencyManagement", "plugins", "parent")

DEFAULT_PLUGIN_GROUP = "org.apache.maven.plugins"

# Property names that reference the enclosing build — never updatable here.
_INTERNAL_PROPS = {
    "version", "revision", "sha1", "changelist",
    "parent.version", "pom.version",
}

_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_CDATA_RE = re.compile(r"<!\[CDATA\[.*?]]>", re.S)

_DEPENDENCY_RE = re.compile(r"<dependency\b[^>]*>.*?</dependency>", re.S)
_PLUGIN_RE = re.compile(r"<plugin\b[^>]*>.*?</plugin>", re.S)
_PARENT_RE = re.compile(r"<parent\b[^>]*>.*?</parent>", re.S)
_PROPERTIES_RE = re.compile(r"<properties\b[^>]*>.*?</properties>", re.S)

_SECTION_RES = {
    "profiles": re.compile(r"<profiles\b[^>]*>.*?</profiles>", re.S),
    "dependencyManagement": re.compile(
        r"<dependencyManagement\b[^>]*>.*?</dependencyManagement>", re.S),
    "build": re.compile(r"<build\b[^>]*>.*?</build>", re.S),
    "reporting": re.compile(r"<reporting\b[^>]*>.*?</reporting>", re.S),
}

_PROP_ENTRY_RE = re.compile(r"<([A-Za-z_][\w.\-]*)>([^<]*)</\1>")
_PROP_REF_RE = re.compile(r"^\$\{([^}]+)\}$")

# Child sections inside a block that may contain foreign <groupId>/<version>
# tags (plugin configuration, plugin-level dependencies, exclusions).
_BLOCK_CUT_RE = re.compile(r"<(configuration|executions|dependencies|exclusions|goals)\b")


@dataclass
class _Block:
    group: str                       # one of GROUPS
    name: str                        # "groupId:artifactId"
    raw_version: str                 # version text as written
    version_span: tuple[int, int]    # absolute span of the version text
    property_name: Optional[str]     # set when the version comes from a property
    current_version: str             # resolved version


@dataclass
class _PomIndex:
    blocks: list[_Block]
    # property name → (value, absolute span of the value text)
    properties: dict[str, tuple[str, tuple[int, int]]]


# ── public API ───────────────────────────────────────────────────────────────

def load(path: str) -> list[DependencyInfo]:
    """Read *path* and return one :class:`DependencyInfo` per updatable entry."""
    raw = Path(path).read_text(encoding="utf-8")
    index = _parse(raw)

    deps: list[DependencyInfo] = []
    seen: set[tuple] = set()
    for block in index.blocks:
        key = (block.name, block.group, block.property_name)
        if key in seen:      # e.g. classifier variants sharing one version
            continue
        seen.add(key)
        deps.append(DependencyInfo(
            name=block.name,
            group=block.group,
            raw_constraint=block.raw_version,
            current_version=block.current_version,
            property_name=block.property_name,
        ))
    return deps


def save(path: str, updates: list[tuple[DependencyInfo, str]]) -> None:
    """
    Apply *updates* (list of (dep, new_version)) to the pom at *path*.

    The file is re-read and re-parsed so replacements land at the current
    positions even if it changed since it was opened.  Property-defined
    versions are updated at the property definition; literal versions are
    replaced in place.  Everything else in the file is left byte-identical.
    """
    raw = Path(path).read_text(encoding="utf-8")
    index = _parse(raw)

    blocks_by_key = {}
    for block in index.blocks:
        blocks_by_key.setdefault((block.name, block.group, block.property_name), block)

    edits: dict[tuple[int, int], str] = {}
    for dep, new_version in updates:
        if dep.property_name is not None:
            entry = index.properties.get(dep.property_name)
            if entry is not None:
                edits[entry[1]] = new_version
        else:
            block = blocks_by_key.get((dep.name, dep.group, None))
            if block is not None:
                edits[block.version_span] = new_version

    if not edits:
        return

    bak = path + ".bak"
    copy2(path, bak)   # backup before any changes

    text = raw
    for (start, end), replacement in sorted(edits.items(), reverse=True):
        text = text[:start] + replacement + text[end:]

    try:
        Path(path).write_text(text, encoding="utf-8")
    except Exception:
        raise   # backup remains so the original can be recovered
    else:
        Path(bak).unlink(missing_ok=True)   # write succeeded — clean up


# ── parsing ──────────────────────────────────────────────────────────────────

def _parse(raw: str) -> _PomIndex:
    scanned = _blank(_blank(raw, _COMMENT_RE), _CDATA_RE)

    sections = {name: [m.span() for m in rx.finditer(scanned)]
                for name, rx in _SECTION_RES.items()}
    plugin_spans = [m.span() for m in _PLUGIN_RE.finditer(scanned)]

    properties = _parse_properties(scanned, sections, plugin_spans)

    blocks: list[_Block] = []

    for m in _DEPENDENCY_RE.finditer(scanned):
        if _inside(m.start(), sections["profiles"]) or _inside(m.start(), plugin_spans):
            continue
        group = ("dependencyManagement"
                 if _inside(m.start(), sections["dependencyManagement"])
                 else "dependencies")
        block = _read_block(scanned, m, group, properties)
        if block is not None:
            blocks.append(block)

    for m in _PLUGIN_RE.finditer(scanned):
        if _inside(m.start(), sections["profiles"]):
            continue
        block = _read_block(scanned, m, "plugins", properties,
                            default_group_id=DEFAULT_PLUGIN_GROUP)
        if block is not None:
            blocks.append(block)

    for m in _PARENT_RE.finditer(scanned):
        if any(_inside(m.start(), sections[s])
               for s in ("profiles", "build", "reporting", "dependencyManagement")):
            continue
        block = _read_block(scanned, m, "parent", properties)
        if block is not None:
            blocks.append(block)
        break   # a pom has at most one project-level <parent>

    return _PomIndex(blocks=blocks, properties=properties)


def _read_block(scanned: str, match: re.Match, group: str,
                properties: dict, default_group_id: str | None = None) -> Optional[_Block]:
    body = match.group(0)
    cut = _BLOCK_CUT_RE.search(body)
    head = body[:cut.start()] if cut else body

    group_id = _tag_text(head, "groupId") or default_group_id
    artifact_id = _tag_text(head, "artifactId")
    if not group_id or not artifact_id:
        return None

    group_id = _resolve_coordinate(group_id, properties)
    artifact_id = _resolve_coordinate(artifact_id, properties)
    if group_id is None or artifact_id is None:
        return None

    version_match = re.search(r"<version>([^<]*)</version>", head)
    if version_match is None:
        return None   # managed by a parent / BOM — nothing to update here

    raw_version, span = _trimmed_span(version_match, offset=match.start())
    resolved, property_name = _resolve_version(raw_version, properties)
    if resolved is None:
        return None

    return _Block(
        group=group,
        name=f"{group_id}:{artifact_id}",
        raw_version=raw_version,
        version_span=span,
        property_name=property_name,
        current_version=resolved,
    )


def _parse_properties(scanned: str, sections: dict, plugin_spans: list) -> dict:
    """The project-level <properties> entries with the spans of their values."""
    for m in _PROPERTIES_RE.finditer(scanned):
        if any(_inside(m.start(), sections[s])
               for s in ("profiles", "build", "reporting")):
            continue
        if _inside(m.start(), plugin_spans):
            continue
        entries: dict[str, tuple[str, tuple[int, int]]] = {}
        for entry in _PROP_ENTRY_RE.finditer(m.group(0)):
            value = entry.group(2).strip()
            start = m.start() + entry.start(2) + (len(entry.group(2)) - len(entry.group(2).lstrip()))
            entries[entry.group(1)] = (value, (start, start + len(value)))
        return entries
    return {}


def _resolve_version(raw: str, properties: dict,
                     ) -> tuple[Optional[str], Optional[str]]:
    """
    Resolve a version reference to (bare_version, property_name).

    ``property_name`` is the property whose *literal* value defines the
    version (following up to three hops of ``${a}`` → ``${b}`` indirection),
    or None for a literal version.  Returns (None, None) for anything that is
    not updatable: internal references, unknown properties, ranges, and the
    LATEST / RELEASE special versions.
    """
    text = raw.strip()
    property_name: Optional[str] = None

    hops = 0
    while (ref := _PROP_REF_RE.match(text)) is not None:
        hops += 1
        if hops > 3:
            return None, None   # unreasonably deep indirection — give up
        prop = ref.group(1).strip()
        if prop in _INTERNAL_PROPS or prop.startswith("project."):
            return None, None
        entry = properties.get(prop)
        if entry is None:
            return None, None
        property_name = prop
        text = entry[0].strip()

    if not text or "${" in text:   # empty or partially interpolated, e.g. 1.2.${patch}
        return None, None
    if text[0] in "[(" or text.upper() in ("LATEST", "RELEASE"):
        return None, None
    return text, property_name


def _resolve_coordinate(text: str, properties: dict) -> Optional[str]:
    """Resolve a groupId/artifactId that may itself be a ${property}."""
    ref = _PROP_REF_RE.match(text.strip())
    if ref is None:
        return text.strip() or None
    entry = properties.get(ref.group(1).strip())
    if entry is None or not entry[0] or _PROP_REF_RE.match(entry[0]):
        return None
    return entry[0]


# ── helpers ──────────────────────────────────────────────────────────────────

def _blank(text: str, regex: re.Pattern) -> str:
    """Replace every match with same-length whitespace so offsets stay valid."""
    return regex.sub(lambda m: " " * (m.end() - m.start()), text)


def _inside(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(start < pos < end for start, end in spans)


def _tag_text(fragment: str, tag: str) -> Optional[str]:
    m = re.search(rf"<{tag}>([^<]*)</{tag}>", fragment)
    return m.group(1).strip() if m else None


def _trimmed_span(match: re.Match, offset: int) -> tuple[str, tuple[int, int]]:
    """The stripped text of capture group 1 and its absolute span."""
    value = match.group(1)
    lead = len(value) - len(value.lstrip())
    stripped = value.strip()
    start = offset + match.start(1) + lead
    return stripped, (start, start + len(stripped))
