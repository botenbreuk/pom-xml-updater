"""
Build-tool abstraction and detection.

Pure Python — no Qt, no settings, no side effects beyond looking for the
Maven Wrapper script inside a project directory.  Given a project directory
this resolves which build tool (Maven / Maven Wrapper / Maven Daemon) drives
the project and builds the correct argv for every command-line operation the
app performs.

Resolution precedence (see ``detect``):

    1. an explicit per-directory override                  (always wins)
    2. a Maven Wrapper script (mvnw) at or above the       (the common case)
       project — walking up for multi-module builds
    3. nothing found                                       → the global default
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Optional

WRAPPER_SCRIPTS = ("mvnw", "mvnw.cmd")


@dataclass(frozen=True)
class _Spec:
    """Static metadata for one build tool."""
    id: str          # stable key: "mvn" | "mvnw" | "mvnd"
    display: str     # human label shown in the UI
    binary: str      # executable name to spawn / resolve on PATH


class BuildTool(Enum):
    """The supported Maven build tools and how to drive each one.

    Members are declared mvn-first; iteration follows this order so candidate
    lists are deterministic.
    """

    MAVEN   = _Spec("mvn",  "Maven",         "mvn")
    WRAPPER = _Spec("mvnw", "Maven Wrapper", "mvnw")
    MVND    = _Spec("mvnd", "Maven Daemon",  "mvnd")

    # ── metadata passthrough ─────────────────────────────────────────────

    @property
    def id(self) -> str:
        return self.value.id

    @property
    def display(self) -> str:
        return self.value.display

    @property
    def binary(self) -> str:
        if self is BuildTool.WRAPPER and sys.platform == "win32":
            return "mvnw.cmd"
        return self.value.binary

    # ── lookup ───────────────────────────────────────────────────────────

    @classmethod
    def from_id(cls, value: "str | BuildTool | None") -> Optional["BuildTool"]:
        """Resolve a tool from its id (case-insensitive) or pass one through.

        Returns ``None`` for unknown / empty values so callers can fall back.
        """
        if isinstance(value, BuildTool):
            return value
        if not value:
            return None
        wanted = value.strip().lower()
        for tool in cls:
            if tool.value.id == wanted:
                return tool
        return None

    # ── command builders ─────────────────────────────────────────────────

    def install_cmd(self) -> list[str]:
        """Download every dependency and plugin declared in pom.xml."""
        return [self.binary, "dependency:resolve"]

    def clean_install_cmd(self) -> list[str]:
        """Force-refresh resolve (also re-checks remote snapshots / metadata)."""
        return [self.binary, "-U", "dependency:resolve"]

    def version_cmd(self) -> list[str]:
        """Print the tool's own version."""
        return [self.binary, "--version"]

    def get_cmd(self, coordinate: str, version: str | None = None) -> list[str]:
        """Fetch a single artifact (optionally pinned to *version*) into ~/.m2."""
        spec = f"{coordinate}:{version}" if version else coordinate
        return [self.binary, "dependency:get", f"-Dartifact={spec}"]


DEFAULT_TOOL = BuildTool.MAVEN


class DetectionSource(str, Enum):
    """Which rule in the precedence chain decided the result."""
    OVERRIDE = "override"
    WRAPPER_SCRIPT = "wrapper-script"
    DEFAULT = "default"


@dataclass(frozen=True)
class Detection:
    """Outcome of :func:`detect`.

    ``wrapper_dir`` is set when a Maven Wrapper script was found, so callers
    can invoke the script from the directory that owns it.
    """
    tool: BuildTool
    source: DetectionSource
    wrapper_dir: Optional[str] = None


def detect(
    project_dir: str,
    *,
    override: "str | BuildTool | None" = None,
    default: "str | BuildTool" = DEFAULT_TOOL,
) -> Detection:
    """Resolve the build tool for *project_dir*.

    ``override`` is a per-directory pin (tool id or instance); ``default``
    is the global fallback used when nothing else applies.  See the module
    docstring for the full precedence.
    """
    # 1. explicit override always wins — no file access needed.
    pinned = BuildTool.from_id(override)
    wrapper_dir = find_wrapper_dir(project_dir) if project_dir else None
    if pinned is not None:
        return Detection(pinned, DetectionSource.OVERRIDE, wrapper_dir)

    fallback = BuildTool.from_id(default) or DEFAULT_TOOL

    if not project_dir:
        return Detection(fallback, DetectionSource.DEFAULT)

    # 2. a Maven Wrapper script at or above the project directory.
    if wrapper_dir is not None:
        return Detection(BuildTool.WRAPPER, DetectionSource.WRAPPER_SCRIPT, wrapper_dir)

    # 3. nothing to go on — use the global default.
    return Detection(fallback, DetectionSource.DEFAULT)


def find_wrapper_dir(start_dir: str) -> Optional[str]:
    """Walk up from *start_dir* to the nearest directory holding a mvnw script."""
    current = os.path.abspath(start_dir)
    while True:
        if any(os.path.isfile(os.path.join(current, script))
               for script in WRAPPER_SCRIPTS):
            return current
        parent = os.path.dirname(current)
        if parent == current:          # reached the filesystem root
            return None
        current = parent


def wrapper_script_path(project_dir: str) -> Optional[str]:
    """Full path to the platform's mvnw script for *project_dir*, or None."""
    wrapper_dir = find_wrapper_dir(project_dir)
    if wrapper_dir is None:
        return None
    preferred = "mvnw.cmd" if sys.platform == "win32" else "mvnw"
    for script in (preferred, *WRAPPER_SCRIPTS):
        candidate = os.path.join(wrapper_dir, script)
        if os.path.isfile(candidate):
            return candidate
    return None
