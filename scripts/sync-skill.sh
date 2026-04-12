#!/usr/bin/env bash
# sync-skill.sh — maintainer helper to refresh subtree-tracked skills.
#
# Usage:
#   scripts/sync-skill.sh <name>     # sync one skill from skills.map
#   scripts/sync-skill.sh --all      # sync every skill in skills.map
#
# Reminder: pulled files become world-readable on toolkit main once pushed.
# Review the diff before pushing.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MAP_FILE="$SCRIPT_DIR/skills.map"

usage() {
  cat >&2 <<EOF
Usage: $0 <skill-name>
       $0 --all

Reads $MAP_FILE (tab-separated: name<TAB>url<TAB>branch)
and runs: git subtree pull --prefix=skills/<name> <url> <branch> --squash
EOF
  exit 2
}

[ $# -eq 1 ] || usage
[ -f "$MAP_FILE" ] || { echo "error: $MAP_FILE not found" >&2; exit 1; }

cd "$REPO_ROOT"

# Refuse to run on a dirty tree — subtree pull needs a clean working tree.
if [ -n "$(git status --porcelain)" ]; then
  echo "error: working tree not clean; commit or stash first" >&2
  exit 1
fi

sync_one() {
  name=$1
  url=$2
  branch=$3
  prefix="skills/$name"

  if [ ! -d "$prefix" ]; then
    echo "error: $prefix does not exist — run 'git subtree add' first" >&2
    return 1
  fi

  echo ">>> syncing $name from $url ($branch)"
  git subtree pull --prefix="$prefix" "$url" "$branch" --squash \
    -m "chore: sync $name skill from upstream"
}

target=$1

# Read the map. Skip blank lines and lines starting with '#'.
# NOTE: bash 3.2 compatible — no mapfile, no associative arrays.
found=0
while IFS=$'\t' read -r name url branch; do
  case "$name" in
    ''|\#*) continue ;;
  esac
  if [ "$target" = "--all" ] || [ "$target" = "$name" ]; then
    sync_one "$name" "$url" "$branch"
    found=1
  fi
done < "$MAP_FILE"

if [ "$found" -eq 0 ]; then
  echo "error: no match for '$target' in $MAP_FILE" >&2
  exit 1
fi

echo ""
echo "Done. Review the diff with 'git log -p HEAD' before 'git push'."
echo "Reminder: pushing makes these files world-readable on the public toolkit."
