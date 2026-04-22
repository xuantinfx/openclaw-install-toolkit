---
phase: 01
title: Images scaffold + build pipeline
status: pending
priority: high
effort: small
---

# Phase 01 — Images scaffold + build pipeline

## Overview

Create the `images/` folder at repo root with 26 placeholder PNG slots in reading-order. Wire `scripts/build-delivery.sh` to require the folder and copy it into each delivery bundle. PDF renderer already handles relative paths — no changes there.

## Key Insights

- `scripts/render-pdf.mjs` uses `md-to-pdf` → Puppeteer, which resolves relative paths from the markdown file's directory. Since templates live at repo root and `images/` also at repo root, `![](images/…)` just works.
- Zip bundle also needs `images/` so users reading the `.md.tmpl` after unzip see screenshots. Two copies in delivery bundle dirs = tiny overhead, strong UX.
- Placeholder PNGs can be a tiny valid PNG copied 26 times — puppeteer will render them as small dots. When user produces real screenshots, they overwrite in-place.

## Requirements

- `images/` folder at repo root.
- 26 files named per brainstorm slot list, valid PNG bytes (smallest transparent PNG is 67 bytes).
- `scripts/build-delivery.sh` must: (a) fail if `images/` missing, (b) copy `images/` into both `delivery/<bundle>/` folders before zipping.

## Related Code Files

**Create:**
- `images/01-botfather-search.png`
- `images/02-botfather-token.png`
- `images/03-anthropic-signup.png`
- `images/04-anthropic-create-key.png`
- `images/05-anthropic-key-reveal.png`
- `images/06-firecrawl-dashboard.png`
- `images/07-firecrawl-create-key.png`
- `images/08-google-ai-studio.png`
- `images/09-google-ai-create-key.png`
- `images/10-brave-dashboard.png`
- `images/11-brave-generate-key.png`
- `images/12-terminal-spotlight.png`
- `images/13-terminal-open.png`
- `images/14-finder-zip.png`
- `images/15-unzipped-folder.png`
- `images/16-way-a-drag.png`
- `images/17-way-b-rightclick.png`
- `images/18-way-b-gatekeeper.png`
- `images/19-installer-running.png`
- `images/20-installer-success.png`
- `images/21-dashboard-opened.png`
- `images/22-telegram-bot-greeting.png`
- `images/23-pairing-message.png`
- `images/24-approval-success.png`
- `images/25-content-monitor-setup.png`
- `images/26-test-run-result.png`
- `images/README.md` — short note: "Placeholder screenshots. Replace each file in-place with the real screenshot. Keep filenames identical; instruction templates reference them directly."

**Modify:**
- `scripts/build-delivery.sh`
  - Add `images` to the `required=(…)` array (around line 38).
  - After the `cp -R skills …` lines (around 93, 96), add `cp -R images "delivery/$single_dir/"` and `cp -R images "delivery/$multi_dir/"`.

## Implementation Steps

1. **Generate a valid minimal PNG once**, then copy into all 26 slots. Smallest valid transparent 1×1 PNG (67 bytes, base64):
   ```
   iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=
   ```
   One-liner to produce the folder:
   ```bash
   mkdir -p images
   SLOTS=(01-botfather-search 02-botfather-token 03-anthropic-signup \
          04-anthropic-create-key 05-anthropic-key-reveal 06-firecrawl-dashboard \
          07-firecrawl-create-key 08-google-ai-studio 09-google-ai-create-key \
          10-brave-dashboard 11-brave-generate-key 12-terminal-spotlight \
          13-terminal-open 14-finder-zip 15-unzipped-folder 16-way-a-drag \
          17-way-b-rightclick 18-way-b-gatekeeper 19-installer-running \
          20-installer-success 21-dashboard-opened 22-telegram-bot-greeting \
          23-pairing-message 24-approval-success 25-content-monitor-setup \
          26-test-run-result)
   PNG_B64='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
   for name in "${SLOTS[@]}"; do
     printf '%s' "$PNG_B64" | base64 --decode > "images/${name}.png"
   done
   ```

2. **Write `images/README.md`** explaining replacement convention.

3. **Update `scripts/build-delivery.sh`:**
   - `required=(install.sh install.command instruction.md.tmpl instruction-multi-user.md.tmpl skills images scripts/render-pdf.mjs scripts/legal-header.md.tmpl scripts/pdf-style.css)`
   - After `cp -R skills "delivery/$single_dir/"`, add: `cp -R images "delivery/$single_dir/"`
   - After `cp -R skills "delivery/$multi_dir/"`, add: `cp -R images "delivery/$multi_dir/"`

4. **Smoke-test:** run `bash scripts/build-delivery.sh --no-zip` (env `CLIENT_NAME=smoke`). Confirm:
   - Script completes without error.
   - `delivery/openclaw-toolkit-single-user-smoke/images/` exists with 26 files.
   - `delivery/openclaw-toolkit-single-user-smoke.pdf` exists and is a valid PDF (`file delivery/*.pdf` should say "PDF document").

## Todo List

- [ ] Create 26 placeholder PNG files via one-liner.
- [ ] Write `images/README.md`.
- [ ] Add `images` to `required` array in `scripts/build-delivery.sh`.
- [ ] Add two `cp -R images` lines in `scripts/build-delivery.sh`.
- [ ] Smoke-run `build-delivery.sh --no-zip` with `CLIENT_NAME=smoke`.
- [ ] Verify PDFs exist and are valid.
- [ ] Verify bundle folders contain `images/` with 26 files.

## Success Criteria

- 26 PNG files in `images/` (byte-valid, any rendering OK).
- `build-delivery.sh --no-zip` succeeds with new required + copy lines.
- Both delivery bundle dirs contain `images/`.
- No PDF render failure (images embed as 1×1 dots — expected until user supplies real ones).

## Risks

| Risk | Mitigation |
|------|------------|
| Placeholder PNG malformed → Puppeteer throws | Use known-good 67-byte 1×1 PNG. Verify with `file images/01-*.png` after generation. |
| `cp -R images` fails if folder missing | Already handled by `required=(…)` fail-fast check. |

## Next Steps

Phase 02 writes the single-user instruction referencing these image paths.
