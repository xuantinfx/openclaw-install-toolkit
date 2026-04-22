---
phase: 04
title: Build + validate delivery
status: pending
priority: medium
effort: small
depends_on: [phase-01, phase-02, phase-03]
---

# Phase 04 — Build + validate delivery

## Overview

Full build of both delivery bundles with the new instruction templates and images folder. Validate PDFs embed images, zips contain images, and the rendered content matches the spec. No code changes in this phase — purely build-and-verify.

## Implementation Steps

1. **Clean build, no zip first (fast iteration):**
   ```bash
   cd /Users/mac/Documents/AI\ project\ x\ a\ Kent/openclaw-toolkit
   CLIENT_NAME="validation test" bash scripts/build-delivery.sh --no-zip
   ```
   Expect exit 0, both bundle folders populated, both PDFs emitted.

2. **Inspect bundle contents:**
   ```bash
   ls -la delivery/openclaw-toolkit-single-user-validation-test/
   ls -la delivery/openclaw-toolkit-single-user-validation-test/images/ | head
   ls -la delivery/openclaw-toolkit-multi-user-validation-test/
   ls -la delivery/openclaw-toolkit-multi-user-validation-test/images/ | head
   ```
   Expected: `install.sh`, `install.command`, `skills/`, `images/` each present. `images/` contains 26 PNGs.

3. **Validate PDFs exist + are PDF:**
   ```bash
   file delivery/*.pdf
   ```
   Expected: each reports `PDF document, version 1.x`.

4. **Open PDFs for manual eyeball:**
   ```bash
   open delivery/openclaw-toolkit-single-user-validation-test.pdf
   open delivery/openclaw-toolkit-multi-user-validation-test.pdf
   ```
   Check:
   - Title line, legal-header stamp, build ID, zip name substituted.
   - Section 2 has 5 key sub-sections with clickable links (links appear blue/underlined in PDF).
   - Checklist table renders as a table.
   - Each `hi`, `openclaw pairing approve …`, `/content-monitor setup`, `manual test run` appears inside a code block with a "⌨️" or "📲" label above it.
   - Image slots render (tiny dots with alt text as tooltip/caption — placeholder PNGs).
   - Cheat-sheet table at end renders correctly.
   - Multi-user PDF has 8 steps instead of 7; "WHAT YOU EACH NEED" block present; port-conflict blurb present.

5. **Run again with zip:**
   ```bash
   CLIENT_NAME="validation test" bash scripts/build-delivery.sh
   ```

6. **Inspect zip contents:**
   ```bash
   unzip -l delivery/openclaw-toolkit-single-user-validation-test.zip | head -40
   unzip -l delivery/openclaw-toolkit-multi-user-validation-test.zip | head -40
   ```
   Expected: `images/` folder listed with 26 PNG entries; `install.sh`, `install.command`, `skills/` subtree also present. No stray files.

7. **Structural grep checks (single-user):**
   ```bash
   grep -c '^## STEP' instruction.md.tmpl         # should be 7
   grep -c '^### [0-9] of 5' instruction.md.tmpl  # should be 5
   grep -oE 'images/[a-z0-9-]+\.png' instruction.md.tmpl | sort -u | wc -l   # ~20-26 unique
   grep -o '{{zip_name}}' instruction.md.tmpl     # at least 1
   ```

8. **Structural grep checks (multi-user):**
   ```bash
   grep -c '^## STEP' instruction-multi-user.md.tmpl  # should be 8
   grep -c '^### [0-9] of 5' instruction-multi-user.md.tmpl  # should be 5
   grep -o '{{zip_name}}' instruction-multi-user.md.tmpl     # at least 1
   grep -c 'port' instruction-multi-user.md.tmpl            # > 0 (port blurb preserved)
   ```

9. **Reference-check image filenames:**
   ```bash
   # All image refs in templates must have matching files in images/
   for f in instruction.md.tmpl instruction-multi-user.md.tmpl; do
     diff <(grep -oE 'images/[a-z0-9-]+\.png' "$f" | sort -u) \
          <(ls images/*.png | sed 's|^|/|;s|^/||' | sort -u) \
          || echo "MISMATCH in $f"
   done
   ```
   Expected: no MISMATCH output. (Diff tolerates extra files in `images/` not referenced — that's OK for now.)

10. **Final delivery inventory:**
    ```bash
    ls -lh delivery/openclaw-toolkit-*.zip delivery/openclaw-toolkit-*.pdf
    ```
    Expected: 2 zips + 2 PDFs, sizes sensible (zip ~200KB–500KB, PDF ~100KB–300KB).

## Todo List

- [ ] `build-delivery.sh --no-zip` succeeds.
- [ ] Both bundle folders contain `images/` with 26 files.
- [ ] Both PDFs are valid PDF files.
- [ ] Manual PDF eyeball: single-user — 7 steps, 5-key section, cheat-sheet, image slots.
- [ ] Manual PDF eyeball: multi-user — 8 steps, per-user warnings, port blurb, cheat-sheet.
- [ ] Full `build-delivery.sh` (with zip) succeeds.
- [ ] Both zips contain `images/` folder with 26 files.
- [ ] Structural grep checks pass for both templates.
- [ ] Image-ref cross-check: no MISMATCH.

## Success Criteria

- Both PDFs render without errors; all image slots visible (even as placeholder dots).
- Both zips contain the complete expected file tree (`install.sh`, `install.command`, `skills/`, `images/`).
- All grep structural checks pass the stated thresholds.
- Image ref cross-check shows no missing files.
- No regression: existing content (Way A/B, troubleshooting, security note, port blurb) present in final output.

## Risks

| Risk | Mitigation |
|------|------------|
| PDF renders but images missing | Puppeteer log inspection + verify placeholder PNGs are valid (`file images/*.png`). |
| Zip excludes `images/` | Verify `scripts/build-delivery.sh` line that copies; re-run. |
| Grep thresholds wrong due to extra/missing step | Adjust counts once real content is written; thresholds above are spec-driven. |

## Next Steps

If all checks pass → mark plan `completed` in frontmatter, run `/ck:journal`, hand off final zips + PDFs to user. If any check fails → fix in the appropriate phase and re-run Phase 04.

## Open Questions

- Should `images/` inside the delivery bundle also include the `README.md` (replacement convention note)? Low stakes — leaving it in for now, user can strip if desired.
- Do we want a companion `/docs/` update noting the new instruction structure? Only if user plans to onboard additional deliveries.
