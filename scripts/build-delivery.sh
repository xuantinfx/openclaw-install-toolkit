#!/usr/bin/env bash
# build-delivery.sh — rebuild customer delivery bundles from repo source.
#
# Produces (ship the .zip + matching .pdf together; folder name matches the
# zip stem so the user's unzip lands in a predictable, self-describing dir):
#   delivery/openclaw-toolkit-single-user-<slug>/      (bundle source)
#   delivery/openclaw-toolkit-multi-user-<slug>/
#   delivery/openclaw-toolkit-single-user-<slug>.zip
#   delivery/openclaw-toolkit-multi-user-<slug>.zip
#   delivery/openclaw-toolkit-single-user-<slug>.pdf   (separate instruction)
#   delivery/openclaw-toolkit-multi-user-<slug>.pdf
#
# Client name sourcing: CLIENT_NAME env var (CI-friendly) OR interactive prompt.
# Build id embedded in each PDF: YYYY-MM-DD-<shortSha>.
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
required=(install.sh install.command \
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

# Build ID: today + git short SHA.
short_sha="$(git rev-parse --short HEAD 2>/dev/null || echo nogit)"
today="$(date +%Y-%m-%d)"
build_id="${today}-${short_sha}"

# Slug: Unicode NFKD → strip combining marks → lowercase → non-alnum to '-'.
slug="$(node -e '
  const s = process.argv[1];
  const slug = s.normalize("NFKD").replace(/\p{M}+/gu,"").toLowerCase()
               .replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"");
  process.stdout.write(slug);
' "$client_name")"
[ -n "$slug" ] || { echo "error: client name slugs to empty string" >&2; exit 2; }

echo "[build] client=\"$client_name\" slug=\"$slug\" build=\"$build_id\""

# Bundle directory names = zip stem, so `unzip` lands users in a folder named
# after the file they double-clicked. Avoids the "where did `single-user/` come
# from?" confusion.
single_dir="openclaw-toolkit-single-user-${slug}"
multi_dir="openclaw-toolkit-multi-user-${slug}"

# Clean previous build so stale files don't leak into the zip. Also sweep the
# pre-rename layout (`single-user/`, `multi-user/`) and any older slug builds.
rm -rf delivery/single-user delivery/multi-user
rm -rf delivery/openclaw-toolkit-single-user-* delivery/openclaw-toolkit-multi-user-*
mkdir -p "delivery/$single_dir" "delivery/$multi_dir"

common=(install.sh install.command)

cp "${common[@]}" "delivery/$single_dir/"
cp -R skills "delivery/$single_dir/"

cp "${common[@]}" "delivery/$multi_dir/"
cp -R skills "delivery/$multi_dir/"

chmod +x "delivery/$single_dir/install.sh" "delivery/$single_dir/install.command"
chmod +x "delivery/$multi_dir/install.sh"  "delivery/$multi_dir/install.command"

# Render PDFs as siblings of the zip (not inside it) so they can be sent as a
# separate attachment. The zip filename is embedded in the instruction so the
# recipient sees the exact name they received.
node scripts/render-pdf.mjs \
  --template instruction.md.tmpl \
  --out "delivery/${single_dir}.pdf" \
  --client "$client_name" --date "$today" --build "$build_id" \
  --zip "${single_dir}.zip"

node scripts/render-pdf.mjs \
  --template instruction-multi-user.md.tmpl \
  --out "delivery/${multi_dir}.pdf" \
  --client "$client_name" --date "$today" --build "$build_id" \
  --zip "${multi_dir}.zip"

if [ "$make_zip" -eq 1 ]; then
  command -v zip >/dev/null 2>&1 || { echo "error: 'zip' not found in PATH" >&2; exit 1; }
  ( cd delivery && zip -qr "${single_dir}.zip" "$single_dir" )
  ( cd delivery && zip -qr "${multi_dir}.zip"  "$multi_dir"  )
fi

printf '\nBuilt delivery bundles:\n'
du -sh "delivery/$single_dir" "delivery/$multi_dir"
if [ "$make_zip" -eq 1 ]; then
  printf '\nDeliverables (ship zip + pdf together):\n'
  ls -lh delivery/*.zip delivery/*.pdf
fi
