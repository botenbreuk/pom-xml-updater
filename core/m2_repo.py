"""
Lookups against the local Maven repository (~/.m2/repository).

Used to detect that a version written to pom.xml has since been resolved
outside the app (a plain ``mvn`` build downloads it), so the "pending"
badge can be cleared — the pom.xml equivalent of comparing lockfile mtimes —
and to read each artifact's human-readable ``<name>`` from its own POM
without going online.
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from functools import cmp_to_key
from pathlib import Path
from typing import Iterator, Optional

from core.maven_versions import compare_versions

_PLACEHOLDER = re.compile(r"\$\{([^}]+)\}")


def default_local_repo() -> Path:
    return Path.home() / ".m2" / "repository"


def artifact_in_local_repo(name: str, version: str,
                           repo_dir: "str | os.PathLike | None" = None) -> bool:
    """True when ``groupId:artifactId`` *name* at *version* exists in the
    local repository (any file present in its version directory)."""
    group_id, _, artifact_id = name.partition(":")
    if not group_id or not artifact_id or not version:
        return False
    repo = Path(repo_dir) if repo_dir is not None else default_local_repo()
    version_dir = repo.joinpath(*group_id.split("."), artifact_id, version)
    try:
        return version_dir.is_dir() and any(version_dir.iterdir())
    except OSError:
        return False


def artifact_pom_name(name: str, version: str,
                      repo_dir: "str | os.PathLike | None" = None) -> Optional[str]:
    """The ``<name>`` that ``groupId:artifactId`` *name* declares in its own
    POM in the local repository, read from *version* when that is
    downloaded, else from the newest version that is.  None when no POM is
    available locally or it declares no usable name."""
    group_id, _, artifact_id = name.partition(":")
    if not group_id or not artifact_id:
        return None
    repo = Path(repo_dir) if repo_dir is not None else default_local_repo()
    artifact_dir = repo.joinpath(*group_id.split("."), artifact_id)
    for v in _versions_to_try(artifact_dir, version):
        pom = artifact_dir / v / f"{artifact_id}-{v}.pom"
        if pom.is_file():
            return _pom_name(pom, group_id, artifact_id, v)
    return None


def _versions_to_try(artifact_dir: Path, version: str) -> Iterator[str]:
    """*version* first, then the other downloaded versions, newest first."""
    if version:
        yield version
    try:
        others = [d.name for d in artifact_dir.iterdir()
                  if d.is_dir() and d.name != version]
    except OSError:
        return
    yield from sorted(others, key=cmp_to_key(compare_versions), reverse=True)


def _pom_name(pom: Path, group_id: str, artifact_id: str, version: str) -> Optional[str]:
    """The project-level ``<name>`` of *pom* with whitespace collapsed and
    ``${...}`` references to the coordinates or the POM's own properties
    filled in.  None when it is missing, empty or still unresolved."""
    try:
        root = ET.parse(pom).getroot()
    except (OSError, ET.ParseError):
        return None
    ns = root.tag[:root.tag.find("}") + 1]     # "{http://maven.apache.org/POM/4.0.0}" or ""
    name = " ".join((root.findtext(f"{ns}name") or "").split())
    if "${" in name:
        known = {f"{prefix}{key}": value
                 for prefix in ("project.", "pom.", "")
                 for key, value in (("groupId", group_id), ("artifactId", artifact_id),
                                    ("version", version))}
        properties = root.find(f"{ns}properties")
        if properties is not None:
            for prop in properties:
                known.setdefault(prop.tag[len(ns):], (prop.text or "").strip())
        name = _PLACEHOLDER.sub(lambda m: known.get(m.group(1), m.group(0)), name)
    return name if name and "${" not in name else None
