---
phase: 03
status: completed
effort: medium
---

# Phase 03 — Wire render into build-delivery.sh

## Context
Modify `scripts/build-delivery.sh` to: prompt for client name (with env override), compute build_id + slug, call the Node renderer twice, stage PDFs (not txt) into bundles, and emit slug-named zips.

## Key Insights
- Keep shell script as the orchestrator; all PDF logic stays in Node (single-responsibility).
- `required=(...)` array must swap `instruction.txt` / `instruction-multi-user.txt` → `instruction.md.tmpl` / `instruction-multi-user.md.tmpl`.
- Slug generation in pure bash is painful for Unicode. Delegate slug + validation to a tiny Node helper (or inline in `render-pdf.mjs` emitting slug to stdout). Cleanest: add `--slug <name>` mode to renderer that prints slug and exits. But YAGNI — simpler to write a 6-line `slugify.mjs` or inline in the build script via `node -e`.
- Decision: **inline `node -e` one-liner** for slug. Zero new files, stays in build script.
- Interactive prompt uses `read -r -p "..."` — already used elsewhere in the repo (see `install.sh`). Reads from `/dev/tty` explicitly to survive being invoked under `npm run` (which can close stdin).
- `CLIENT_NAME` env override: `client_name="${CLIENT_NAME:-}"; if empty → prompt`.
- Empty-slug guard: abort with clear error so we never ship an untagged zip.
- `--no-zip` path: still generates PDFs; just skips zip step (existing flag semantics).

## Requirements
- Prompt works when script invoked via `npm run build-delivery` (stdin may be piped).
- `CLIENT_NAME="Foo Bar"` skips prompt.
- Build ID reflects current commit + `-dirty` when tree dirty.
- Zip names: `delivery/openclaw-toolkit-single-user-<slug>.zip`, `...-multi-user-<slug>.zip`.
- PDFs land at `delivery/single-user/instruction.pdf` and `delivery/multi-user/instruction-multi-user.pdf`.
- `delivery/single-user/` and `delivery/multi-user/` MUST NOT contain any `.txt` or `.md.tmpl`.
- Script exits non-zero on: empty slug, renderer failure, missing required source file.

## Related Code Files
- **Modify**: `scripts/build-delivery.sh`
- **Read (unchanged)**: `package.json`, `scripts/render-pdf.mjs`, `instruction.md.tmpl`, `instruction-multi-user.md.tmpl`

## Implementation Steps

### 3.1 Update `required` array
Swap `.txt` references for new `.md.tmpl` files:
```bash
required=(install.sh install.command README.md \
          instruction.md.tmpl instruction-multi-user.md.tmpl skills \
          scripts/render-pdf.mjs scripts/legal-header.md.tmpl scripts/pdf-style.css)
```

### 3.2 Read client name
Insert after the `cd "$REPO_ROOT"` line:
```bash
client_name="${CLIENT_NAME:-}"
if [ -z "$client_name" ]; then
  if [ -r /dev/tty ]; then
    printf 'Client name (as it should appear on the PDF): ' >/dev/tty
    IFS= read -r client_name </dev/tty
  else
    echo "error: no CLIENT_NAME env var and no TTY to prompt" >&2
    exit 2
  fi
fi
client_name="${client_name##[[:space:]]}"; client_name="${client_name%%[[:space:]]}"
[ -n "$client_name" ] || { echo "error: client name is empty" >&2; exit 2; }
```

### 3.3 Compute build_id
```bash
short_sha="$(git rev-parse --short HEAD 2>/dev/null || echo nogit)"
dirty=""
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then dirty="-dirty"; fi
today="$(date +%Y-%m-%d)"
build_id="${today}-${short_sha}${dirty}"
```

### 3.4 Compute slug
Inline Node one-liner for Unicode NFKD + strip marks + kebab:
```bash
slug="$(node -e '
  const s = process.argv[1];
  const slug = s.normalize("NFKD").replace(/[̀-ͯ]/g,"").toLowerCase()
               .replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"");
  process.stdout.write(slug);
' "$client_name")"
[ -n "$slug" ] || { echo "error: client name slugs to empty string" >&2; exit 2; }
```

### 3.5 Generate PDFs (replace existing instruction-copy lines)
Before the `cp "${common[@]}" …` lines, do:
```bash
node scripts/render-pdf.mjs \
  --template instruction.md.tmpl \
  --out delivery/single-user/instruction.pdf \
  --client "$client_name" --date "$today" --build "$build_id"

node scripts/render-pdf.mjs \
  --template instruction-multi-user.md.tmpl \
  --out delivery/multi-user/instruction-multi-user.pdf \
  --client "$client_name" --date "$today" --build "$build_id"
```
Remove the old `cp … instruction.txt …` and `cp … instruction-multi-user.txt …` lines.

Note: `mkdir -p delivery/single-user delivery/multi-user` must happen BEFORE renderer invocation (renderer writes into them). Existing script already does this — confirm ordering when editing.

### 3.6 Update zip naming
Replace the two zip commands with:
```bash
if [ "$make_zip" -eq 1 ]; then
  command -v zip >/dev/null 2>&1 || { echo "error: 'zip' not found in PATH" >&2; exit 1; }
  ( cd delivery && zip -qr "openclaw-toolkit-single-user-${slug}.zip" single-user )
  ( cd delivery && zip -qr "openclaw-toolkit-multi-user-${slug}.zip"  multi-user  )
fi
```
Also update the final `ls -lh delivery/*.zip` — it already uses glob, still works.

### 3.7 Sanity: stage info line
Before building, echo a one-liner so the operator sees what's being produced:
```bash
echo "[build] client=\"$client_name\" slug=\"$slug\" build=\"$build_id\""
```

## Todo List
- [x] Update `required=(...)` array (swap txt → md.tmpl, add render assets)
- [x] Insert client-name read (prompt + env override) with trim + empty guard
- [x] Insert build_id computation (date + short sha + dirty)
- [x] Insert slug computation (inline `node -e`) + empty guard
- [x] Replace txt `cp` calls with two `node scripts/render-pdf.mjs` invocations
- [x] Update zip commands to include slug in filename
- [x] Add `[build]` info echo before staging
- [x] Manual smoke test: `CLIENT_NAME="Jack Carter" npm run build-delivery --silent --no-zip`

## Implementation Notes
- TTY detection: `[ -r /dev/tty ]` is unreliable (path may exist but open may fail with "Device not configured" in some non-interactive contexts). Replaced with active open-probe `{ : </dev/tty; } 2>/dev/null` which actually tries to open the TTY before committing to the interactive path. Test T4 (no env + no TTY) confirmed exit code 2 with correct error.
- Whitespace trim: used pure-bash parameter expansion `${var#...}` / `${var%...}` with `[![:space:]]` character-class patterns — avoids external `tr`/`sed` invocation for a one-shot trim.
- Slug regex uses `\p{M}` Unicode combining-mark property (with `u` flag) rather than the original `[̀-ͯ]` hard-coded range — covers more diacritic scripts while being clearer.

## Success Criteria
- `CLIENT_NAME="Jack Carter" bash scripts/build-delivery.sh --no-zip` succeeds silently; both PDFs land in respective `delivery/*/` folders; no txt files present.
- Unset `CLIENT_NAME` + interactive terminal → prompt appears, input "Jack Carter", build completes.
- Unset `CLIENT_NAME` + piped stdin (no /dev/tty) → exits with error code 2.
- Empty input at prompt → exits with error code 2.
- Full run produces slug-named zips in `delivery/`.

## Risk Assessment
- **Risk**: `read </dev/tty` fails when TTY is absent (CI). **Mitigation**: covered by the env-override path + explicit exit code 2 when both are missing.
- **Risk**: `node -e` slug command fails silently if Node not installed. **Mitigation**: add `command -v node >/dev/null || { echo …; exit 1; }` near top of script.
- **Risk**: Script previously wiped `delivery/single-user` and `delivery/multi-user` — confirm wipe still happens BEFORE staging so stale PDFs don't leak.

## Security Considerations
- Client name flows through shell via env var / prompt → passed as a CLI arg to `node` and `render-pdf.mjs`. Always quoted (`"$client_name"`); no eval. Safe.
- Slug path components are `[a-z0-9-]` only by construction. No path traversal.

## Next Steps
- Phase 04 runs end-to-end verification.
