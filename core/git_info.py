"""
Lightweight git status helpers for the start screen.

All operations are purely local (no network fetch), so they are fast
enough to run synchronously while building the recent-files list.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Optional

_git_available: Optional[bool] = None


def is_git_available() -> bool:
    """Return True if git is on PATH. Result is cached after the first call."""
    global _git_available
    if _git_available is None:
        try:
            r = subprocess.run(["git", "--version"], capture_output=True, timeout=3)
            _git_available = r.returncode == 0
        except Exception:
            _git_available = False
    return _git_available


@dataclass
class GitInfo:
    branch: str
    behind: int  # commits behind upstream; 0 = synced or no upstream configured


def get_git_info(directory: str) -> Optional[GitInfo]:
    """Return GitInfo for *directory*, or None if it is not inside a git repo."""

    def _run(args: list[str]) -> tuple[int, str]:
        try:
            r = subprocess.run(
                ["git", "-C", directory] + args,
                capture_output=True, text=True, timeout=3,
            )
            return r.returncode, r.stdout.strip()
        except Exception:
            return 1, ""

    rc, _ = _run(["rev-parse", "--git-dir"])
    if rc != 0:
        return None

    rc, branch = _run(["rev-parse", "--abbrev-ref", "HEAD"])
    if rc != 0 or not branch:
        return None

    # Count commits the local branch is behind its upstream tracking branch.
    # Uses the local reflog — no network access.
    rc, behind_str = _run(["rev-list", "HEAD..@{u}", "--count"])
    behind = int(behind_str) if rc == 0 and behind_str.isdigit() else 0

    return GitInfo(branch=branch, behind=behind)
