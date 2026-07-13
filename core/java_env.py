"""
Utility for building a subprocess environment that can find java / Maven.

macOS GUI apps start with a minimal PATH that often omits Homebrew and SDKMAN
bin dirs, so ``java`` / ``mvn`` can't be found via their bare command names.
This module resolves the most common install locations at runtime and makes
sure JAVA_HOME is set when the platform can tell us.
"""
from __future__ import annotations

import os
import subprocess
import sys


def _sdkman_bin_dirs() -> list[str]:
    """Return SDKMAN candidate bin dirs (java, maven, mvnd) that exist."""
    candidates_dir = os.path.expanduser("~/.sdkman/candidates")
    if not os.path.isdir(candidates_dir):
        return []
    dirs: list[str] = []
    for candidate in ("java", "maven", "mvnd"):
        path = os.path.join(candidates_dir, candidate, "current", "bin")
        if os.path.isdir(path):
            dirs.append(path)
    return dirs


def _default_java_home() -> str | None:
    """Ask macOS for the default JDK via /usr/libexec/java_home."""
    if sys.platform != "darwin":
        return None
    try:
        r = subprocess.run(["/usr/libexec/java_home"],
                           capture_output=True, text=True, timeout=5)
        home = r.stdout.strip()
        return home if r.returncode == 0 and os.path.isdir(home) else None
    except Exception:
        return None


def java_path_env() -> dict:
    """Return ``os.environ`` with common java/Maven install dirs prepended to PATH."""
    env = os.environ.copy()
    home = os.path.expanduser("~")

    extras: list[str] = [
        "/usr/local/bin",                                    # Homebrew Intel / classic
        "/opt/homebrew/bin",                                 # Homebrew Apple Silicon
        "/opt/homebrew/sbin",
        "/opt/local/bin",                                    # MacPorts
        f"{home}/.jenv/shims",                               # jenv
        f"{home}/.asdf/shims",                               # asdf
        f"{home}/.local/share/mise/shims",                   # mise
        *_sdkman_bin_dirs(),                                 # SDKMAN java / maven / mvnd
    ]

    java_home = env.get("JAVA_HOME") or _default_java_home()
    if java_home:
        env["JAVA_HOME"] = java_home
        java_bin = os.path.join(java_home, "bin")
        if os.path.isdir(java_bin):
            extras.insert(0, java_bin)

    current = env.get("PATH", "")
    current_parts = set(current.split(os.pathsep))
    new_parts = [p for p in extras if p not in current_parts]
    if new_parts:
        env["PATH"] = os.pathsep.join(new_parts) + os.pathsep + current
    return env
