#!/usr/bin/env bash
# build-delivery.sh — rebuild customer delivery bundles from repo source.
#
# Produces:
#   delivery/single-user/   (install.sh, install.command, instruction.txt,
#                            README.md, skills/)
#   delivery/multi-user/    (same + instruction-multi-user.txt, which is an
#                            addendum referencing instruction.txt sections A/B)
#   delivery/openclaw-toolkit-single-user.zip
#   delivery/openclaw-toolkit-multi-user.zip
#
# Usage:
#   scripts/build-delivery.sh            # rebuild both folders and zips
#   scripts/build-delivery.sh --no-zip   # skip the zip step

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

make_zip=1
case "${1-}" in
  --no-zip) make_zip=0 ;;
  "")       ;;
  *) echo "usage: $0 [--no-zip]" >&2; exit 2 ;;
esac

cd "$REPO_ROOT"

# Verify source files exist before we start wiping the delivery tree.
required=(install.sh install.command README.md instruction.txt instruction-multi-user.txt skills)
for f in "${required[@]}"; do
  [ -e "$f" ] || { echo "error: missing source file: $f" >&2; exit 1; }
done

# Clean previous build so stale files don't leak into the zip.
rm -rf delivery/single-user delivery/multi-user
rm -f  delivery/openclaw-toolkit-single-user.zip delivery/openclaw-toolkit-multi-user.zip
mkdir -p delivery/single-user delivery/multi-user

common=(install.sh install.command README.md)

# Each bundle ships exactly one instruction file — both are self-contained,
# no cross-references between them.
cp "${common[@]}" instruction.txt delivery/single-user/
cp -R skills delivery/single-user/

cp "${common[@]}" instruction-multi-user.txt delivery/multi-user/
cp -R skills delivery/multi-user/

chmod +x delivery/single-user/install.sh  delivery/single-user/install.command
chmod +x delivery/multi-user/install.sh   delivery/multi-user/install.command

if [ "$make_zip" -eq 1 ]; then
  command -v zip >/dev/null 2>&1 || { echo "error: 'zip' not found in PATH" >&2; exit 1; }
  ( cd delivery && zip -qr openclaw-toolkit-single-user.zip single-user )
  ( cd delivery && zip -qr openclaw-toolkit-multi-user.zip  multi-user )
fi

printf '\nBuilt delivery bundles:\n'
du -sh delivery/single-user delivery/multi-user
if [ "$make_zip" -eq 1 ]; then
  printf '\nZips:\n'
  ls -lh delivery/*.zip
fi
