"""
Lookups against the local Maven repository (~/.m2/repository).

Used to detect that a version written to pom.xml has since been resolved
outside the app (a plain ``mvn`` build downloads it), so the "pending"
badge can be cleared — the pom.xml equivalent of comparing lockfile mtimes.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


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
