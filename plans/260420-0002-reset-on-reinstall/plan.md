---
status: code-complete (live E2E deferred)
created: 2026-04-20
scope: reset-on-reinstall
blockedBy: []
blocks: []
supersedes-behavior-in: ../260419-1825-zip-based-install/
review: ../reports/code-reviewer-260420-1103-reset-on-reinstall.md
---

# Auto-reset on Reinstall — Implementation Plan

When `install.sh` detects an existing OpenClaw install, offer a TTY-gated y/N prompt to run `openclaw reset --scope full --yes --non-interactive` before proceeding. Default = skip wipe. Under `curl|bash` (no TTY) → auto-skip. Two new flags: `--reset` (force) and `--keep-data` (force skip).

## Context Links
- Upstream CLI docs (verified 2026-04-20 via context7 + docs.openclaw.ai):
  - `openclaw reset --scope <config|config+creds+sessions|full> --yes --non-interactive` — keeps CLI, wipes state
  - `openclaw uninstall --all` — also removes CLI binary → reinstall loop, NOT used
- Current installer: `install.sh` lines 230-269 (backup config + overwrite skills). Phase 01 hooks here.
- Predecessor plan (code-complete): `../260419-1825-zip-based-install/plan.md`

## Key Locked Decisions
- Use `openclaw reset --scope full` (not `uninstall`). Reset keeps CLI so upstream installer call stays idempotent and fast.
- Default behavior under TTY: prompt `[warn] existing install found at ~/.openclaw — wipe before reinstall? [y/N]`. Default N for safety.
- Default behavior WITHOUT TTY (curl|bash): auto-skip wipe, print notice. Fail-safe: never destroy without explicit consent.
- Flags: `--reset` forces wipe (skip prompt), `--keep-data` forces skip (skip prompt). Mutually exclusive.
- If `openclaw` binary missing but `~/.openclaw/` present (broken install): log warning, skip reset, let upstream installer + our config write rebuild from scratch.
- If `openclaw reset` returns non-zero: abort with clear error. Don't blindly `rm -rf` as fallback (safety over convenience).
- Detection signal: existence of `$OPENCLAW_HOME/openclaw.json`. Directory alone is not enough (upstream creates empty `bin/` on fresh install before config).

## Out of Scope
- Legacy paths (`~/.clawdbot`, `~/.moltbot`). Upstream `reset` doesn't touch them per docs; we inherit that gap.
- Wiping the npm-global CLI binary. That's `uninstall --app` territory.
- Auto-revoking OAuth/API tokens server-side.

## Phases
| # | Name | File | Status |
|---|---|---|---|
| 01 | Add reset-on-reinstall to install.sh + docs | `phase-01-add-reset-flow.md` | done |
| 02 | Manual validation | `phase-02-validation.md` | automated PASS; live E2E deferred |

## Post-Review Hardenings (applied 2026-04-20)
- **C1** Moved detection above the dry-run remap by capturing `ORIGINAL_OPENCLAW_HOME` before the mktemp swap. `--dry-run --reset` now correctly previews against the user's real `~/.openclaw`.
- **H1** Coerced `OPENCLAW_RESET` / `OPENCLAW_KEEP_DATA` to 0/1 from `1|true|yes|on` (case-insensitive). Avoids `[: integer expression expected` under `set -euo pipefail`.
- **H2** Snapshot config to `openclaw.json.pre-reset.bak.$ts` before destructive call. `die` message names the snapshot path for recovery.
- **M3** Mirror user's prompt choice to stderr (`[reset] user choice: <reset|skip>`) so audit logs preserve intent.
- **TTY probe** Replaced `[ -r /dev/tty ] && [ -w /dev/tty ]` with `: </dev/tty >/dev/tty 2>/dev/null` — actually opens the device, defeating the macOS false-positive where the node exists but `open()` returns ENXIO under no-controlling-terminal.

## Dependencies
- Phase 02 requires Phase 01 merged.

## Success Criteria
- Fresh machine install: no prompt shown, behavior identical to today.
- Second install with TTY + user types `y`: `~/.openclaw` wiped clean, new install succeeds, bot still replies.
- Second install with TTY + user types `N` (or Enter): current backup-config behavior preserved exactly.
- `curl|bash` re-install: skips wipe silently with one-line notice, never blocks.
- `install.sh --reset` under any TTY state: wipes without prompting.
- `install.sh --keep-data` under any TTY state: skips wipe without prompting.
- `install.sh --reset --keep-data`: exits with usage error (mutually exclusive).
- If `openclaw` binary missing but config present: print warning, skip reset, continue install. No crash.

## Risk Summary
- User double-clicks `install.command` expecting just a config refresh → sees wipe prompt → panic. Mitigation: prompt wording makes it clear default is N (safe).
- Reset removes credentials + sessions; user may not have bot token saved elsewhere. Mitigation: installer re-prompts for token anyway, upstream `reset --scope full` is documented to nuke creds + sessions.
- `openclaw reset` behavior may drift across CLI versions. Mitigation: pin verification to exit code; abort on non-zero rather than guessing.

## Open Questions
- Should `--reset` also drop the npm-installed `openclaw` binary (i.e. run `openclaw uninstall --app` too)? Current plan: no. Reset-only is faster + avoids npm global churn. Revisit if reinstalls stop curing CLI-level corruption.
