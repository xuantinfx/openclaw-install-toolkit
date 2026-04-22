#!/usr/bin/env bash
# build-delivery.sh — rebuild customer delivery bundles from repo source.
#
# Produces:
#   delivery/single-user/   (install.sh, install.command, README.md, skills/,
#                            instruction.pdf — personalized per client)
#   delivery/multi-user/    (same + instruction-multi-user.pdf)
#   delivery/openclaw-toolkit-single-user-<slug>.zip
#   delivery/openclaw-toolkit-multi-user-<slug>.zip
#
# Client name sourcing: CLIENT_NAME env var (CI-friendly) OR interactive prompt.
# Build id embedded in each PDF: YYYY-MM-DD-<shortSha>[-dirty].
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

command -v node >/dev/null 2>&1 || { echo "error: 'node' not found in PATH" >&2; exit 1; }

# Verify source files exist before we start wiping the delivery tree.
required=(install.sh install.command README.md \
          instruction.md.tmpl instruction-multi-user.md.tmpl skills \
          scripts/render-pdf.mjs scripts/legal-header.md.tmpl scripts/pdf-style.css)
for f in "${required[@]}"; do
  [ -e "$f" ] || { echo "error: missing source file: $f" >&2; exit 1; }
done

# Client name: env override OR interactive prompt via /dev/tty (survives `npm run`).
# `[ -r /dev/tty ]` isn't reliable — /dev/tty path may exist but fail to open
# when there is no controlling terminal. Probe by actually opening it.
client_name="${CLIENT_NAME:-}"
if [ -z "$client_name" ]; then
  if { : </dev/tty; } 2>/dev/null; then
    printf 'Client name (as it should appear on the PDF): ' >/dev/tty
    IFS= read -r client_name </dev/tty
  else
    echo "error: no CLIENT_NAME env var and no TTY to prompt" >&2
    exit 2
  fi
fi
# Trim leading/trailing whitespace.
client_name="${client_name#"${client_name%%[![:space:]]*}"}"
client_name="${client_name%"${client_name##*[![:space:]]}"}"
[ -n "$client_name" ] || { echo "error: client name is empty" >&2; exit 2; }

# Build ID: today + git short SHA + optional -dirty.
short_sha="$(git rev-parse --short HEAD 2>/dev/null || echo nogit)"
dirty=""
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then dirty="-dirty"; fi
today="$(date +%Y-%m-%d)"
build_id="${today}-${short_sha}${dirty}"

# Slug: Unicode NFKD → strip combining marks → lowercase → non-alnum to '-'.
slug="$(node -e '
  const s = process.argv[1];
  const slug = s.normalize("NFKD").replace(/\p{M}+/gu,"").toLowerCase()
               .replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"");
  process.stdout.write(slug);
' "$client_name")"
[ -n "$slug" ] || { echo "error: client name slugs to empty string" >&2; exit 2; }

echo "[build] client=\"$client_name\" slug=\"$slug\" build=\"$build_id\""

# Clean previous build so stale files don't leak into the zip.
rm -rf delivery/single-user delivery/multi-user
rm -f  delivery/openclaw-toolkit-single-user-*.zip delivery/openclaw-toolkit-multi-user-*.zip
mkdir -p delivery/single-user delivery/multi-user

common=(install.sh install.command README.md)

cp "${common[@]}" delivery/single-user/
cp -R skills delivery/single-user/

cp "${common[@]}" delivery/multi-user/
cp -R skills delivery/multi-user/

node scripts/render-pdf.mjs \
  --template instruction.md.tmpl \
  --out delivery/single-user/instruction.pdf \
  --client "$client_name" --date "$today" --build "$build_id"

node scripts/render-pdf.mjs \
  --template instruction-multi-user.md.tmpl \
  --out delivery/multi-user/instruction-multi-user.pdf \
  --client "$client_name" --date "$today" --build "$build_id"

chmod +x delivery/single-user/install.sh  delivery/single-user/install.command
chmod +x delivery/multi-user/install.sh   delivery/multi-user/install.command

if [ "$make_zip" -eq 1 ]; then
  command -v zip >/dev/null 2>&1 || { echo "error: 'zip' not found in PATH" >&2; exit 1; }
  ( cd delivery && zip -qr "openclaw-toolkit-single-user-${slug}.zip" single-user )
  ( cd delivery && zip -qr "openclaw-toolkit-multi-user-${slug}.zip"  multi-user  )
fi

printf '\nBuilt delivery bundles:\n'
du -sh delivery/single-user delivery/multi-user
if [ "$make_zip" -eq 1 ]; then
  printf '\nZips:\n'
  ls -lh delivery/*.zip
fi
