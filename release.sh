#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Pom.xml Updater Release ==="
echo ""

# ── git state checks ───────────────────────────────────────────────────────────
if git rev-parse @{u} &>/dev/null; then
  read -ra SYNC_COUNT <<< "$(git rev-list --left-right --count @{u}..)"
  COMMITS_BEHIND=${SYNC_COUNT[0]}
  COMMITS_AHEAD=${SYNC_COUNT[1]}
  if [[ "$COMMITS_BEHIND" != "0" ]]; then
    echo "ERROR: $COMMITS_BEHIND commit(s) behind upstream. Pull before releasing."
    exit 1
  fi
  if [[ "$COMMITS_AHEAD" != "0" ]]; then
    echo "ERROR: $COMMITS_AHEAD commit(s) ahead of upstream. Push your changes first."
    exit 1
  fi
fi

if [[ -n "$(git diff)" ]]; then
  echo "ERROR: You have unstaged changes. Commit or stash before releasing."
  exit 1
fi

if [[ -n "$(git diff --staged)" ]]; then
  echo "ERROR: You have staged changes. Commit or stash before releasing."
  exit 1
fi

# ── current version ────────────────────────────────────────────────────────────
CURRENT_VERSION=$(grep -oE '[0-9]+\.[0-9]+\.[0-9]+' "$SCRIPT_DIR/_version.py")
echo "Current version: $CURRENT_VERSION"

read -p "New version [e.g. 1.2.0]: " NEW_VERSION

if [[ ! "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "ERROR: Invalid version '$NEW_VERSION'. Expected X.Y.Z"
  exit 1
fi

if git tag | grep -qx "v$NEW_VERSION"; then
  echo "ERROR: Tag v$NEW_VERSION already exists."
  exit 1
fi

echo ""
echo "Releasing v$NEW_VERSION..."

# ── bump version files ─────────────────────────────────────────────────────────
_sed() {
  if [[ "$(uname)" == "Darwin" ]]; then
    sed -i '' "$@"
  else
    sed -i "$@"
  fi
}

_sed "s/VERSION = \"[^\"]*\"/VERSION = \"$NEW_VERSION\"/" "$SCRIPT_DIR/_version.py"
_sed "s/^version = \"[^\"]*\"/version = \"$NEW_VERSION\"/" "$SCRIPT_DIR/pyproject.toml"

echo "✓  Updated _version.py and pyproject.toml"

# ── commit and tag ─────────────────────────────────────────────────────────────
git -C "$SCRIPT_DIR" add _version.py pyproject.toml
git -C "$SCRIPT_DIR" commit -m "Released: $NEW_VERSION"
git -C "$SCRIPT_DIR" tag "v$NEW_VERSION"

echo "✓  Committed and tagged v$NEW_VERSION"

# ── bump to dev version ────────────────────────────────────────────────────────
IFS='.' read -r MAJOR MINOR PATCH <<< "$NEW_VERSION"
DEFAULT_DEV="$MAJOR.$MINOR.$((PATCH + 1)).dev0"

read -p "Next dev version? [Defaults to $DEFAULT_DEV] " DEV_VERSION
DEV_VERSION=${DEV_VERSION:-$DEFAULT_DEV}

_sed "s/VERSION = \"[^\"]*\"/VERSION = \"$DEV_VERSION\"/" "$SCRIPT_DIR/_version.py"
_sed "s/^version = \"[^\"]*\"/version = \"$DEV_VERSION\"/" "$SCRIPT_DIR/pyproject.toml"

git -C "$SCRIPT_DIR" add _version.py pyproject.toml
git -C "$SCRIPT_DIR" commit -m "Changed to dev: $DEV_VERSION"

echo "✓  Bumped to $DEV_VERSION"

# ── push ───────────────────────────────────────────────────────────────────────
read -p "Push branch and tag to origin? [Y/n] " PUSH_ANSWER
PUSH_ANSWER=${PUSH_ANSWER:-Y}
if [[ "$PUSH_ANSWER" =~ ^[Yy]$ ]]; then
  BRANCH=$(git -C "$SCRIPT_DIR" rev-parse --abbrev-ref HEAD)
  git -C "$SCRIPT_DIR" push origin "$BRANCH"
  git -C "$SCRIPT_DIR" push origin "v$NEW_VERSION"
  echo "✓  Pushed $BRANCH and v$NEW_VERSION to origin"
fi

echo ""
echo "=== Released v$NEW_VERSION ==="
