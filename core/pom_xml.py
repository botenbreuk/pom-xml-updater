"""
Read and update Maven pom.xml files while preserving formatting.
No Qt dependency — pure Python.

The file is parsed with expat, the standard library's XML parser, but never
written back from the parse result: ElementTree or minidom would re-serialize
the whole file, rewriting the XML declaration, multi-line tags, empty tags
and character references.  Instead the parse records the byte offset of each
version text, and save() replaces only those bytes, so everything else
(comments, line endings, the file's encoding) stays byte-identical.

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
from dataclasses import dataclass, field
from pathlib import Path
from shutil import copy2
from typing import Iterator, Optional
from xml.parsers import expat

from models.dependency import DependencyInfo

GROUPS = ("dependencies", "dependencyManagement", "plugins", "parent")

DEFAULT_PLUGIN_GROUP = "org.apache.maven.plugins"

# Property names that reference the enclosing build — never updatable here.
_INTERNAL_PROPS = {
    "version", "revision", "sha1", "changelist",
    "parent.version", "pom.version",
}

# The element path below <project> of each group's entries.  Nothing else is
# read: not <profiles>, a plugin's own <dependencies> or <configuration>, or
# a dependency's <exclusions>.
_ENTRY_PATHS = {
    ("dependencies", "dependency"): "dependencies",
    ("dependencyManagement", "dependencies", "dependency"): "dependencyManagement",
    ("build", "plugins", "plugin"): "plugins",
    ("build", "pluginManagement", "plugins", "plugin"): "plugins",
    ("reporting", "plugins", "plugin"): "plugins",
    ("parent",): "parent",
}
_ENTRY_PATH_PREFIXES = {path[:i] for path in _ENTRY_PATHS for i in range(1, len(path))}

# load() lists dependencies first, then plugins, then the parent, each in
# document order.
_GROUP_ORDER = {"dependencies": 0, "dependencyManagement": 0, "plugins": 1, "parent": 2}

_PROP_REF_RE = re.compile(r"^\$\{([^}]+)\}$")


@dataclass
class _Element:
    """An element of the parsed pom."""
    tag: str                                    # as written, e.g. "guava.version"
    children: list[_Element] = field(default_factory=list)
    # The element's own text in the chunks expat reports: (byte offset in the
    # file, text).  The offset is None where the file's bytes are not
    # literally that text, e.g. for &#46;.
    chunks: list[tuple[Optional[int], str]] = field(default_factory=list)

    @property
    def name(self) -> str:
        """The tag without a namespace prefix."""
        return self.tag.rpartition(":")[2]

    def child(self, name: str) -> Optional[_Element]:
        return next((c for c in self.children if c.name == name), None)

    def child_text(self, name: str) -> Optional[str]:
        child = self.child(name)
        return None if child is None else child.value()[0]

    def value(self) -> tuple[str, Optional[tuple[int, int]]]:
        """
        The stripped text, and the byte span that save() may replace with a
        new value: only set when the text is one plain run of bytes in the
        file.  A comment beside the text is fine; a reference inside it isn't.
        """
        text = "".join(chunk for _, chunk in self.chunks).strip()
        runs = [(at, chunk) for at, chunk in self.chunks if chunk.strip()]
        if len(runs) != 1 or runs[0][0] is None:
            return text, None
        at, chunk = runs[0]
        start = at + len(chunk) - len(chunk.lstrip())
        return text, (start, start + len(text))


@dataclass
class _Block:
    group: str                       # one of GROUPS
    name: str                        # "groupId:artifactId"
    raw_version: str                 # version text as written
    version_span: tuple[int, int]    # byte span of the version text in the file
    property_name: Optional[str]     # set when the version comes from a property
    current_version: str             # resolved version


@dataclass
class _PomIndex:
    blocks: list[_Block]
    # property name → (value, byte span of the value, or None if that can't
    # be replaced in place)
    properties: dict[str, tuple[str, Optional[tuple[int, int]]]]


# ── public API ───────────────────────────────────────────────────────────────

def load(path: str) -> list[DependencyInfo]:
    """
    Read *path* and return one :class:`DependencyInfo` per updatable entry.

    Raises :class:`xml.parsers.expat.ExpatError` when the file isn't
    well-formed XML, and :class:`ValueError` when it isn't a pom.
    """
    index = _parse(Path(path).read_bytes())

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
    data = Path(path).read_bytes()
    index = _parse(data)

    blocks_by_key = {}
    for block in index.blocks:
        blocks_by_key.setdefault((block.name, block.group, block.property_name), block)

    edits: dict[tuple[int, int], bytes] = {}
    for dep, new_version in updates:
        if dep.property_name is not None:
            entry = index.properties.get(dep.property_name)
            if entry is not None and entry[1] is not None:
                edits[entry[1]] = new_version.encode("ascii")
        else:
            block = blocks_by_key.get((dep.name, dep.group, None))
            if block is not None:
                edits[block.version_span] = new_version.encode("ascii")

    if not edits:
        return

    bak = path + ".bak"
    copy2(path, bak)   # backup before any changes

    for (start, end), replacement in sorted(edits.items(), reverse=True):
        data = data[:start] + replacement + data[end:]

    try:
        Path(path).write_bytes(data)
    except Exception:
        raise   # backup remains so the original can be recovered
    else:
        Path(bak).unlink(missing_ok=True)   # write succeeded — clean up


# ── parsing ──────────────────────────────────────────────────────────────────

def _parse(data: bytes) -> _PomIndex:
    project = _read_tree(data)

    section = project.child("properties")
    properties = ({entry.tag: entry.value() for entry in section.children}
                  if section is not None else {})

    entries = sorted(_entries(project), key=lambda entry: _GROUP_ORDER[entry[0]])
    blocks = [block for group, element in entries
              if (block := _read_block(element, group, properties)) is not None]
    return _PomIndex(blocks=blocks, properties=properties)


def _read_tree(data: bytes) -> _Element:
    """Parse *data*, the file's bytes, and return its <project> element."""
    parser = expat.ParserCreate()
    roots: list[_Element] = []
    stack: list[_Element] = []

    def start(tag: str, _attributes: dict) -> None:
        element = _Element(tag)
        (stack[-1].children if stack else roots).append(element)
        stack.append(element)

    def end(_tag: str) -> None:
        stack.pop()

    def text(chunk: str) -> None:
        # With buffer_text off (the default), CurrentByteIndex is where the
        # chunk starts in *data*.  Keep that offset only if the bytes there
        # are this very text: not for a reference such as &#46; (or &amp;,
        # whose "&" would match its first byte), a CRLF delivered as "\n",
        # or non-ASCII text.
        at: Optional[int] = parser.CurrentByteIndex
        if (at < 0 or chunk.startswith("&") or not chunk.isascii()
                or not data.startswith(chunk.encode("ascii"), at)):
            at = None
        element = stack[-1]
        if at is not None and element.chunks:
            last_at, last = element.chunks[-1]
            if last_at is not None and last_at + len(last) == at:
                element.chunks[-1] = (last_at, last + chunk)   # one run, split by expat
                return
        element.chunks.append((at, chunk))

    def skipped(name: str, is_parameter_entity: bool) -> None:
        # An entity expat doesn't know, such as &oslash; in a developer's
        # name: Maven predefines the XHTML entities.  Its text is unknown
        # here, so a value containing it can't be replaced.
        if stack and not is_parameter_entity:
            stack[-1].chunks.append((None, f"&{name};"))

    # As if there were an external DTD: an undeclared entity is then skipped
    # instead of being an error.
    parser.UseForeignDTD(True)
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = text
    parser.SkippedEntityHandler = skipped
    parser.Parse(data, True)

    project = roots[0]
    if project.name != "project":
        raise ValueError(f"not a Maven pom: the root element is <{project.tag}>, "
                         "not <project>")
    return project


def _entries(node: _Element,
             path: tuple[str, ...] = ()) -> Iterator[tuple[str, _Element]]:
    """(group, element) for every entry below *node*, in document order."""
    for child in node.children:
        child_path = (*path, child.name)
        if child_path in _ENTRY_PATHS:
            yield _ENTRY_PATHS[child_path], child
        elif child_path in _ENTRY_PATH_PREFIXES:
            yield from _entries(child, child_path)


def _read_block(element: _Element, group: str, properties: dict) -> Optional[_Block]:
    group_id = element.child_text("groupId")
    if not group_id and group == "plugins":
        group_id = DEFAULT_PLUGIN_GROUP
    artifact_id = element.child_text("artifactId")
    if not group_id or not artifact_id:
        return None

    group_id = _resolve_coordinate(group_id, properties)
    artifact_id = _resolve_coordinate(artifact_id, properties)
    if group_id is None or artifact_id is None:
        return None

    version = element.child("version")
    if version is None:
        return None   # managed by a parent / BOM — nothing to update here

    raw_version, span = version.value()
    if span is None:
        return None   # empty, or not plain text in the file — can't be replaced
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


def _resolve_version(raw: str, properties: dict,
                     ) -> tuple[Optional[str], Optional[str]]:
    """
    Resolve a version reference to (bare_version, property_name).

    ``property_name`` is the property whose *literal* value defines the
    version (following up to three hops of ``${a}`` → ``${b}`` indirection),
    or None for a literal version.  Returns (None, None) for anything that is
    not updatable: internal references, unknown properties, property values
    that can't be replaced in place, ranges, and the LATEST / RELEASE special
    versions.
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
        if entry is None or entry[1] is None:
            return None, None
        property_name = prop
        text = entry[0]

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
