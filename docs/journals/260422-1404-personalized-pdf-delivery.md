# Personalized PDF Delivery: Plan Execution Complete

**Date**: 2026-04-22 14:04  
**Severity**: Low (feature delivery)  
**Component**: Instruction delivery pipeline  
**Status**: Resolved  

## What Happened

Executed the 4-phase plan to replace legacy `.txt` instruction files with per-client personalized PDFs. Templated instructions (`instruction.md.tmpl`, `instruction-multi-user.md.tmpl`), built a Puppeteer-based renderer (`scripts/render-pdf.mjs`), rewrote the delivery pipeline (`build-delivery.sh`), and validated against 10-row test matrix. Feature is complete and committed at `0727e40`.

## The Brutal Truth

The commit subject is misleading garbage. Git-manager tagged it `docs(plans):` when the diff contains feature code (new scripts, deps, templates, shell rewrite). Conventional commit scopes should reflect what changed, not what was planning vehicle. This will confuse future devs grepping for "feat:" or "chore:" on the delivery system. Should have been `feat(delivery): pdf rendering and client-specific instruction packaging` or similar. Small but annoying win condition fail.

## Technical Details

**TTY Detection:** The original plan used `[ -r /dev/tty ]` which returns true even when the file can't be opened ("Device not configured" on macOS with no controlling terminal). Test T4 caught this returning exit 1 instead of 2. Fixed with active open-probe: `{ : </dev/tty; } 2>/dev/null` which only succeeds when redirection actually works.

**Build Performance:** Each `build-delivery` invocation takes ~5 minutes wall clock, almost entirely Puppeteer/Chromium spinup (2x, once per PDF). Actual CPU time is <5s. This matters for CI budgeting — we're bottlenecked on browser initialization, not rendering.

**Unicode Slug Handling:** Used `\p{M}` combining-mark property instead of the plan's literal `[̀-ͯ]` range. Handles more scripts cleanly. Verified: `Nguyễn Văn A → nguyen-van-a`.

## What We Tried

- Plain `[ -r /dev/tty ]` for TTY detection → failed on macOS (test T4 caught it)
- Switched to `{ : </dev/tty; } 2>/dev/null` → passed all terminal-detection tests
- Used plan's Unicode range `[̀-ͯ]` for combining marks → switched to `\p{M}` for clarity and coverage

## Root Cause Analysis

The TTY check surfaced a classic Unix-ism: test operators can give false positives when the underlying syscall will fail. The fix (active open-probe) is the correct pattern — we now test the actual operation, not just file existence. All other phases executed cleanly; no hidden surprises.

## Lessons Learned

1. **Commit subjects matter as much as diffs.** A misleading scope will cause archaeological pain later. Conventional commit is a contract with future readers.
2. **TTY detection in shell requires an actual open attempt,** not just a test. Document this pattern for next cross-platform shell work.
3. **Browser spinup is your bottleneck in PDF pipelines.** If perf matters, consider caching a running browser instance or pre-warming Chromium at deploy time.

## Next Steps

1. **Amend the commit message** to reflect the actual dominant change (feature code, not planning docs). This is a low-effort, high-value fix for git archaeology.
2. **Document the TTY detection pattern** in code comments or a small dev doc for future shell scripts.
3. **Monitor build-delivery perf** in CI — 5 min per invocation is acceptable but document it for deployment planning.
