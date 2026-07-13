"""
Maven Central HTTP client and version filtering.
No Qt dependency — pure Python.

The authoritative version list comes from ``maven-metadata.xml`` on
``repo1.maven.org`` (always current).  Per-version publish timestamps come
from the Central search API (``search.maven.org``, ``core=gav``) — best
effort, since that index can lag behind the repository; versions without a
known timestamp pass the age filter and simply show no age.  The
source-repository link is read from the ``<scm>`` section of the newest
stable version's pom — best effort, one extra request per artifact.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

import requests

from .maven_versions import is_stable, categorize_bump, max_version, numeric_parts

SEARCH_URL = "https://search.maven.org/solrsearch/select"
REPO_URL = "https://repo1.maven.org/maven2"
TIMEOUT = 15   # seconds
PAGE_SIZE = 200
MAX_PAGES = 5  # cap: 1000 versions; histories longer than that lose the oldest entries


class MavenFetchError(Exception):
    pass


def fetch_package_data(name: str, min_age_days: int) -> dict:
    """
    Fetch all published versions of ``groupId:artifactId`` *name* and return:
        {
          'versions': [str, ...],      # stable versions passing the age filter
          'age_map':  {version: days-since-publication | None},
          'time_map': {version: ISO timestamp},
          'repo_url': str | None,
        }

    ``min_age_days`` filters out versions published more recently than
    that many days ago (0 = no filter).
    """
    group_id, _, artifact_id = name.partition(":")
    if not group_id or not artifact_id:
        raise MavenFetchError(f"'{name}' is not a valid groupId:artifactId coordinate.")

    all_versions = _metadata_versions(group_id, artifact_id)
    time_map = _search_timestamps(group_id, artifact_id)
    if not all_versions:
        # metadata missing (relocated / non-canonical coordinate) — fall back
        # to whatever the search index knows.
        all_versions = list(time_map)
    if not all_versions:
        raise MavenFetchError(f"Artifact '{name}' was not found on Maven Central.")

    stable_versions = [v for v in all_versions if is_stable(v)]
    old_enough = [v for v in stable_versions if _is_old_enough(time_map, v, min_age_days)]

    age_map: dict[str, Optional[int]] = {
        v: _age_days(time_map, v) for v in old_enough
    }

    newest_stable = None
    for v in stable_versions:
        newest_stable = max_version(newest_stable, v)

    return {
        "versions": old_enough,
        "age_map": age_map,
        "time_map": time_map,
        "repo_url": _fetch_repo_url(group_id, artifact_id, newest_stable),
    }


def resolve_updates(
    current_version: str,
    registry_result: dict,
) -> dict:
    """
    Given the current version and the dict returned by fetch_package_data,
    find the best patch / minor / major upgrade that passed the age filter.

    Returns:
        {
          'latest_patch': str | None,
          'latest_minor': str | None,
          'latest_major': str | None,
          'patch_age':    int | None,
          'minor_age':    int | None,
          'major_age':    int | None,
          'current_age':  int | None,
          'repo_url':     str | None,
        }
    """
    best: dict[str, Optional[str]] = {"patch": None, "minor": None, "major": None}
    age_map = registry_result.get("age_map", {})
    time_map = registry_result.get("time_map", {})

    # Anchor check: filter out higher candidates that were published before
    # the current version — guards against artifacts that changed versioning
    # conventions over time (date-style versions, renumbered lines).
    #
    # For minor/patch bumps we anchor against the publish date of the current
    # version; for major bumps against the earliest publish date in the
    # current major series, so a new major released before later maintenance
    # patches of the old major is still offered.
    current_published = _parse_ts(time_map.get(current_version))
    first_in_current_major = _earliest_in_major(time_map, current_version)

    for v in registry_result.get("versions", []):
        bump = categorize_bump(current_version, v)
        if not bump:
            continue
        anchor = first_in_current_major if bump == "major" else current_published
        if anchor is not None:
            v_published = _parse_ts(time_map.get(v))
            if v_published is not None and v_published <= anchor:
                continue
        best[bump] = max_version(best[bump], v)

    return {
        "latest_patch": best["patch"],
        "latest_minor": best["minor"],
        "latest_major": best["major"],
        "patch_age": age_map.get(best["patch"]) if best["patch"] else None,
        "minor_age": age_map.get(best["minor"]) if best["minor"] else None,
        "major_age": age_map.get(best["major"]) if best["major"] else None,
        "current_age": _age_days(time_map, current_version),
        "repo_url": registry_result.get("repo_url"),
    }


# ── internal helpers ─────────────────────────────────────────────────────────

_METADATA_VERSION_RE = re.compile(r"<version>([^<]+)</version>")


def _metadata_versions(group_id: str, artifact_id: str) -> list[str]:
    """The complete, current version list from repo1's maven-metadata.xml."""
    url = (f"{REPO_URL}/{group_id.replace('.', '/')}/{artifact_id}/"
           "maven-metadata.xml")
    try:
        resp = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise MavenFetchError(str(exc)) from exc
    if resp.status_code == 404:
        return []
    if not resp.ok:
        raise MavenFetchError(
            f"Maven Central returned HTTP {resp.status_code} "
            f"for '{group_id}:{artifact_id}'.")
    return [m.group(1).strip() for m in _METADATA_VERSION_RE.finditer(resp.text)]


def _search_timestamps(group_id: str, artifact_id: str) -> dict[str, str]:
    """Per-version publish timestamps from the search index — best effort."""
    try:
        docs = _search_all_versions(group_id, artifact_id)
    except MavenFetchError:
        return {}
    time_map: dict[str, str] = {}
    for doc in docs:
        version = doc.get("v")
        ts = doc.get("timestamp")
        if isinstance(version, str) and isinstance(ts, (int, float)):
            time_map[version] = datetime.fromtimestamp(
                ts / 1000, tz=timezone.utc).isoformat()
    return time_map


def _search_all_versions(group_id: str, artifact_id: str) -> list[dict]:
    """Page through the Central search API's per-version (gav) documents."""
    docs: list[dict] = []
    start = 0
    while True:
        params = {
            "q": f'g:"{group_id}" AND a:"{artifact_id}"',
            "core": "gav",
            "rows": PAGE_SIZE,
            "start": start,
            "wt": "json",
        }
        try:
            resp = requests.get(SEARCH_URL, params=params,
                                headers={"Accept": "application/json"},
                                timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise MavenFetchError(str(exc)) from exc

        if not resp.ok:
            raise MavenFetchError(
                f"Maven Central search returned HTTP {resp.status_code} "
                f"for '{group_id}:{artifact_id}'.")
        try:
            body = resp.json()
        except ValueError as exc:
            raise MavenFetchError(
                f"Invalid JSON from Maven Central for '{group_id}:{artifact_id}'.") from exc

        response = body.get("response", {})
        page = response.get("docs", [])
        docs.extend(page)

        start += PAGE_SIZE
        if not page or start >= response.get("numFound", 0) or start >= PAGE_SIZE * MAX_PAGES:
            return docs


def _is_old_enough(time_map: dict, version: str, min_age_days: int) -> bool:
    if min_age_days <= 0:
        return True
    if version not in time_map:
        return True  # unknown publish date — let it through
    days = _age_days(time_map, version)
    return days is None or days >= min_age_days


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _earliest_in_major(time_map: dict, current_version: str) -> Optional[datetime]:
    """The earliest publish date of any version in current_version's major series."""
    current = numeric_parts(current_version)
    if current is None:
        return None
    dates = []
    for version, ts in time_map.items():
        parts = numeric_parts(version)
        if parts is not None and parts[0] == current[0]:
            dt = _parse_ts(ts)
            if dt is not None:
                dates.append(dt)
    return min(dates) if dates else None


def _age_days(time_map: dict, version: str) -> Optional[int]:
    published = _parse_ts(time_map.get(version))
    if published is None:
        return None
    return (datetime.now(timezone.utc) - published).days


def _fetch_repo_url(group_id: str, artifact_id: str,
                    version: Optional[str]) -> Optional[str]:
    """Read the <scm> / <url> of the newest stable pom — best effort."""
    if not version:
        return None
    pom_url = (f"{REPO_URL}/{group_id.replace('.', '/')}/{artifact_id}/"
               f"{version}/{artifact_id}-{version}.pom")
    try:
        resp = requests.get(pom_url, timeout=10)
        if not resp.ok:
            return None
        text = resp.text
    except requests.RequestException:
        return None

    scm = re.search(r"<scm>(.*?)</scm>", text, re.S)
    if scm:
        url = re.search(r"<url>\s*([^<\s]+)\s*</url>", scm.group(1))
        if url:
            normalized = _normalize_repo_url(url.group(1))
            if normalized:
                return normalized
    url = re.search(r"<url>\s*(https?://[^<\s]+)\s*</url>", text)
    return _normalize_repo_url(url.group(1)) if url else None


def _normalize_repo_url(raw: str) -> Optional[str]:
    """Normalise scm-style URLs to a browseable https:// URL."""
    raw = re.sub(r"^scm:git[:@]?", "", raw)
    raw = re.sub(r"^git\+", "", raw)
    raw = re.sub(r"^git://", "https://", raw)
    raw = re.sub(r"^ssh://[^@]+@", "https://", raw)
    m = re.match(r"^git@([^:]+):(.+)$", raw)   # git@github.com:user/repo
    if m:
        raw = f"https://{m.group(1)}/{m.group(2)}"
    raw = re.sub(r"\.git$", "", raw.rstrip("/"))

    # Drop unresolved-property suffixes like .../tree/${project.scm.tag}
    # and the path segments they leave dangling.
    if "${" in raw:
        raw = raw.split("${", 1)[0]
        parts = raw.rstrip("/").split("/")
        while parts and parts[-1] in ("tree", "blob", "browse", "tags", ""):
            parts.pop()
        raw = "/".join(parts)

    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return None
