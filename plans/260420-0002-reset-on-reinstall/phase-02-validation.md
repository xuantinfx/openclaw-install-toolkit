# Phase 02 — Manual validation matrix

## Overview
- **Priority:** High
- **Status:** automated PASS (T1, T5, T5b, T6, T7, T8, H1+, no-TTY) — live E2E (T12) deferred
- **Effort:** ~30min on a real Mac, ~15min on Linux

## Automated PASS log (2026-04-20)
- T1 fresh `--dry-run` → no reset lines
- T5 `--dry-run --reset` (config + binary) → `[dry-run] would snapshot ... and run: openclaw reset`
- **T5b** real `$HOME/.openclaw/openclaw.json` + `--dry-run --reset` → snapshot+run line uses real path (C1 regression cover)
- T6 `--dry-run --keep-data` → `[info] keeping existing data`
- T7 `--reset --keep-data` → `error: --reset and --keep-data are mutually exclusive`, exit 1
- T8 `OPENCLAW_RESET=1` → matches T5
- H1+ `OPENCLAW_RESET=true` → behaves as T5; `OPENCLAW_RESET=garbage` → no error, treated as 0
- No-TTY (`</dev/null`) + config present → `[info] existing install detected ... — skipping wipe (no TTY)`
- shellcheck install.sh → clean
- bash -n install.sh → clean

## Test Matrix

| # | Precondition | Command | Expected |
|---|---|---|---|
| T1 | no `~/.openclaw/openclaw.json` | `bash install.sh --dry-run` | No reset prompt, no reset log, dry-run completes |
| T2 | config present, TTY | `bash install.sh --dry-run`, answer `N` | Skip log, backup-config behavior proceeds |
| T3 | config present, TTY | `bash install.sh --dry-run`, answer `y` | `[dry-run] would run: openclaw reset ...` line printed, install continues |
| T4 | config present, no TTY | `bash install.sh --dry-run </dev/null` | `[info] existing install detected ... skipping wipe (no TTY)` log |
| T5 | config present | `bash install.sh --dry-run --reset` | No prompt, prints dry-run line for reset |
| T6 | config present | `bash install.sh --dry-run --keep-data` | No prompt, skip log, continues |
| T7 | any state | `bash install.sh --reset --keep-data` | Usage error on mutual exclusivity, exit non-zero |
| T8 | any state | `OPENCLAW_RESET=1 bash install.sh --dry-run` | Same as T5 |
| T9 | any state | `OPENCLAW_KEEP_DATA=1 bash install.sh --dry-run` | Same as T6 |
| T10 | config present, `openclaw` binary missing from PATH + `$OPENCLAW_HOME/bin` | `bash install.sh --reset` | Aborts with "cannot reset: openclaw binary not found ..." |
| T11 | config present, binary missing, no `--reset` | `bash install.sh`, answer `y` at prompt | Logs warning, skips reset, continues install |
| T12 | **real install** config present, TTY, answer `y` | `bash install.sh` (full run, not dry) | `~/.openclaw/openclaw.json` gone pre-install, new token prompts appear, bot replies to "hi" within 2 min |

## Environment Setup

- Use a spare macOS user account or a throwaway `OPENCLAW_HOME_OVERRIDE=/tmp/openclaw-test-$$` for destructive tests. NEVER run T12 on a primary dev machine without backing up `~/.openclaw/openclaw.json` first.
- For T10/T11: temporarily move binary aside — `mv $(command -v openclaw) /tmp/openclaw.bak` and restore after.

## Success Criteria
- All 12 rows pass.
- No shellcheck regressions (`shellcheck install.sh`).
- Re-run T12 a second time (now "first install" again after the wipe) → behavior identical to today's first-run path.

## Notes
- T4's `</dev/null` redirect is a cheap stand-in for the `curl|bash` no-TTY case; the production flow is `bash <(curl ...)` where `/dev/tty` is usually still attached. If T4 passes but a real `curl|bash` pipe still blocks, the `/dev/tty` probe is wrong — re-check `[ -r /dev/tty ] && [ -w /dev/tty ]`.
