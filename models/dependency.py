from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class DependencyInfo:
    name: str             # Maven coordinate "groupId:artifactId"
    group: str            # 'dependencies' | 'dependencyManagement' | 'plugins' | 'parent'
    raw_constraint: str   # version text as written in pom.xml, e.g. '1.2.3' or '${spring.version}'
    current_version: str  # resolved version, e.g. '1.2.3'

    # Set when the version is defined via a <properties> entry:
    property_name: Optional[str] = None

    # The <name> from the artifact's own POM in the local repository (None = unknown):
    pom_name: Optional[str] = None

    # Populated after the Maven Central fetch:
    latest_patch: Optional[str] = None
    latest_minor: Optional[str] = None
    latest_major: Optional[str] = None

    # Publish ages (days) for each update:
    patch_age: Optional[int] = None
    minor_age: Optional[int] = None
    major_age: Optional[int] = None

    # Days since the current version was published (None = unknown):
    current_age: Optional[int] = None

    # Repository link (populated after fetch):
    repo_url: Optional[str] = None

    # Transient UI state:
    fetch_status: str = "pending"   # 'pending' | 'loading' | 'done' | 'error'
    error_message: str = ""
    needs_install: bool = False

    # Version the user clicked (not yet written to disk):
    pending_version: Optional[str] = None

    @property
    def row_key(self) -> tuple:
        return (self.name, self.group, self.property_name)

    @property
    def group_label(self) -> str:
        labels = {
            "dependencies": "dep",
            "dependencyManagement": "depMgmt",
            "plugins": "plugin",
            "parent": "parent",
        }
        return labels.get(self.group, self.group)

    @property
    def has_any_update(self) -> bool:
        return any(v is not None for v in [self.latest_patch, self.latest_minor, self.latest_major])
