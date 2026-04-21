---
status: complete
created: 2026-04-21
completed: 2026-04-21
slug: fresh-device-install-fixes
---

# Fresh-Device Install Fixes

## Goal

Fix the 4 LIKELY findings from the env-risk review so non-technical users on pre-Sequoia macOS, non-zsh shells, and quarantined zips don't hit first-five-minutes failures.

## Context

- Source report: `plans/reports/env-risk-260421-1121-fresh-device-install.md`
- 4 LIKELY / 6 POSSIBLE / 4 UNLIKELY findings total
- Scope here: LIKELY only (L1–L4). Possibles/unlikelys deferred.

## Decisions

| # | Decision | Rationale |
|---|---|---|
| jq strategy | **Auto-bootstrap** (download from GitHub releases to `$OPENCLAW_HOME/bin/jq` on missing jq) | No zip bloat; install.sh already requires network for upstream installer. Fallback to improved hint if download fails. |
| Multi-rc write | **Always write `.zshrc`; also write `.bash_profile` and `.bashrc` if they exist** | Dodges `$SHELL` vs actual interactive-shell mismatch. Idempotent — existing skip-if-present check stays. |
| jq version pin | **jq 1.7.1** | Well-tested, stable, GitHub-hosted. Upgrade later when needed. |
| SHA256 pinning | **Skip for now** | HTTPS to github.com/jqlang is acceptable for a bootstrap tool. Adds hash-verify complexity without meaningful threat reduction. |
| Way A promotion | **Add one-sentence preamble + tighten Way B label** | KISS — just docs tweak. No script change. |

## Phases (single plan, no subfiles — each change is small)

| # | Change | File | Status |
|---|---|---|---|
| 1 | `bootstrap_jq_if_missing()` + preflight wire-in | install.sh | complete |
| 2 | Rewrite `ensure_openclaw_on_path()` for multi-rc | install.sh | complete |
| 3 | Promote Way A in STEP 2 | instruction.txt | complete |
| 4 | Regression test matrix + new scenarios | — | complete |

## Success Criteria

1. Fresh-Mac simulation (no jq on PATH) → bootstrap fetches jq and install continues; non-technical user sees no error.
2. Install writes PATH export to `.zshrc` AND to `.bash_profile`/`.bashrc` when those exist.
3. `instruction.txt` STEP 2 opens with a clear "use Way A to avoid Gatekeeper" note.
4. All prior dry-run tests still pass (17/17).
5. New tests: jq-bootstrap path, multi-rc write, Way-A preamble.

## Deferred (POSSIBLE findings, not fixed here)

- P1 npm as hard dep
- P3 locale edge cases
- P6 /dev/tcp on custom bashes
- Linux support tightening (unresolved Q5)

## Risks

- **jq GitHub release URL changes** → bootstrap breaks silently. Mitigation: version-pin 1.7.1, fall through to improved hint on 404.
- **User without network at preflight** → bootstrap fails, hint still guides them. Same as today, not worse.
- **Corporate proxy blocking github.com** → same fallback.
