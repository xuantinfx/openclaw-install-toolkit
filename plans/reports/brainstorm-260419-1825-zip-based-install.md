---
type: brainstorm
date: 2026-04-19 18:25 (+07)
slug: zip-based-install
status: approved
---

# Zip-based Install Flow — Brainstorm Report

## Problem Statement

Current install flow hits `github.com/xuantinfx/openclaw-install-toolkit` twice via `curl | bash`:

1. STEP 2 — fetches `install.sh` (then curls `openclaw.ai/install-cli.sh`)
2. STEP 5 — fetches `install-skill.sh` (then downloads full repo tarball to extract `skills/`)

Goal: deliver one per-user zip via message. User unzips, runs locally. Only allowed network call = `openclaw.ai` installer (+ Telegram/Anthropic verify). Zero requests to toolkit GitHub repo after delivery.

## Requirements

**Functional**
- Single zip contains everything needed to install.
- Script runs end-to-end from unzipped folder — no re-fetch of its own assets.
- Still prompts for Telegram token + Anthropic key (no baked secrets).
- Telegram bot + gateway + skills all working after one invocation.

**Non-functional**
- Bash 3.2 compatible (stock macOS). Same dep set: `curl`, `jq`, `tar` no longer needed.
- Config file still mode 0600 at `~/.openclaw/openclaw.json`.
- No requests to `github.com/xuantinfx/*` at runtime.
- Preserve existing error handling, validation, verify steps.

**Audience**
- Non-technical macOS user ("no coding background" per `instruction.txt`). Must survive Gatekeeper + lost exec bit.

## Evaluated Approaches

### A — One merged `install.sh` + local `skills/` copy (CHOSEN)
Zip ships `install.sh`, `install.command`, `skills/`. Script resolves own dir, does openclaw install then `cp -R skills/* ~/.openclaw/skills/`.

Pros: single entry point, minimal moving parts, matches "1 zip → implement step by step".
Cons: zip rebuild needed when skills change. Acceptable — delivery is manual anyway.

### B — Keep 2 scripts, both local
Ship `install.sh` + `install-skill.sh`, both read from `./skills/`. User runs both sequentially.

Pros: smallest diff from today.
Cons: two commands for one goal. `install-skill.sh` becomes a local-copy wrapper — thin enough that it's dead weight.

### C — Bundle `install-cli.sh` from openclaw.ai too
Pin openclaw's installer inside zip. Fully offline install.

Pros: zero runtime network except verify.
Cons: ships stale installer until re-bundled; drifts from upstream on every openclaw release. User explicitly said "only openclaw installer" requests are allowed — no need to eliminate them.

**Decision: A.** Merges install-skill into install, drops tarball fetch, keeps openclaw.ai curl (per user).

## Chosen Solution

### Zip layout
```
openclaw-toolkit.zip
├── install.sh          — merged installer (openclaw + local skills)
├── install.command     — double-click Terminal wrapper
├── skills/             — snapshot of all skill dirs from repo
│   └── content-monitor/...
└── README.txt          — 5-line quickstart (optional)
```

### Runtime flow
1. `preflight` — curl + jq present, not inside git worktree.
2. `collect_secrets` — prompt Telegram token + Anthropic key via `/dev/tty`.
3. `validate_secrets` — regex + format checks.
4. `run_official_installer` — `curl openclaw.ai/install-cli.sh | bash` (unchanged).
5. `ensure_openclaw_on_path` — probe `$OPENCLAW_HOME/bin` + npm + Homebrew paths, edit `~/.zshrc` / `~/.bash_profile` (unchanged).
6. `backup_and_write_config` — write `~/.openclaw/openclaw.json` mode 0600 (unchanged).
7. `start_daemon` — `openclaw gateway install` (unchanged).
8. `wait_for_healthz` — poll `127.0.0.1:18789/healthz` up to 30s (unchanged).
9. `verify_telegram` — `getMe` round-trip (unchanged).
10. `verify_anthropic` — `/v1/models` round-trip (unchanged).
11. **NEW** `install_local_skills` — `cp -R "$SCRIPT_DIR/skills/"* ~/.openclaw/skills/`, validate each has `SKILL.md`, reject symlinks.
12. `on_success` — same success banner + bot username.

### Entry points
- **Primary** (documented first): Open Terminal → type `bash ` (with trailing space) → drag `install.sh` from Finder → press Enter. Works regardless of exec bit + Gatekeeper.
- **Secondary**: Double-click `install.command`. Needs exec bit + Gatekeeper bypass (right-click → Open on first run).

### Network surface at runtime
| Host | Purpose | Allowed |
|---|---|---|
| openclaw.ai | Fetch `install-cli.sh` | Yes (user rule) |
| api.telegram.org | Verify bot token | Yes |
| api.anthropic.com | Verify API key | Yes |
| npm registry (via `install-cli.sh`) | openclaw binary install | Yes (upstream's call) |
| github.com/xuantinfx | — | **No** (goal) |

## Implementation Considerations

### File changes
| File | Action | Notes |
|---|---|---|
| `install.sh` | Edit | Add `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`. Add `install_local_skills()`. Call after verify steps, before `on_success`. |
| `install-skill.sh` | Delete | Merged into install.sh. |
| `install.command` | New | 3 lines: `cd "$(dirname "$0")"` + `bash install.sh` + keep terminal open on error (`read -p "Press Enter to close..."`). |
| `instruction.txt` | Rewrite | Collapse STEP 2 + STEP 5 into single "Unzip and run" step. Document both entry points. Add Gatekeeper note. |
| `README.md` | Minor | Reflect new flow. |
| `scripts/build-zip.sh` | Out of scope | Separate task per user. |

### Skills-copy logic (ported from install-skill.sh)
- Source: `$SCRIPT_DIR/skills/` must exist, be a directory, no symlinks.
- Each subdir must contain `SKILL.md` (sanity check vs corrupt zip).
- Destination: `~/.openclaw/skills/<name>/` — wipe + copy (matches current overwrite behaviour).
- No skill-name filter — always install all shipped skills (YAGNI).

### Known risks
1. **Gatekeeper on `install.command`** — first double-click triggers "cannot verify developer". Mitigation: instruction.txt primary path uses drag-to-Terminal (unaffected); secondary path documents right-click → Open.
2. **Exec bit loss** — some unzip apps strip `+x`. Primary drag-to-Terminal flow uses `bash <path>`, so exec bit irrelevant. Secondary `.command` flow breaks silently if stripped — documented fallback: `chmod +x install.command install.sh` in Terminal.
3. **Missing `./skills/`** — if zip is corrupted/repacked wrong, skills step must fail loudly with actionable error. Handled by existing validation pattern.
4. **Skills drift** — zip snapshot diverges from repo over time. Rebuild zip each delivery. Acceptable for manual-delivery model.
5. **Path with spaces** — script runs from `openclaw-toolkit/` which users may unzip into e.g. `~/Downloads/`. All paths must quote `"$SCRIPT_DIR"`. Current install.sh already disciplined here.
6. **Second run on same machine** — current `install.sh` is idempotent (backs up existing `openclaw.json`, `openclaw gateway install` is idempotent). Skills copy overwrites — matches current behaviour. No regression.

### Security considerations
- Zip delivery via messaging apps — out of scope for script, but worth noting: zips contain no secrets at rest, so interception ≠ credential leak.
- Symlink check on extracted skills tree preserved — guards against malicious repack.
- `~/.openclaw/openclaw.json` still 0600. Unchanged.
- Refuse-to-run inside git worktree still enforced (prevents committing secrets).

## Success Metrics
- Fresh macOS Sonoma+: unzip → drag install.sh to Terminal → bot replies to "hi" within 2 min.
- Packet capture during install shows zero requests to `github.com/xuantinfx/*`.
- `~/.openclaw/skills/content-monitor/SKILL.md` exists post-install.
- `openclaw --version` works in a new Terminal after install completes.
- Re-running install.sh on same machine doesn't break existing install (idempotency).

## Validation Plan
- Manual dry-run: `OPENCLAW_HOME_OVERRIDE=/tmp/ocw-test ./install.sh --dry-run` — confirm skills copy path logic without touching real `~/.openclaw`.
- Manual end-to-end on clean macOS VM / fresh user account.
- `tcpdump -i any host github.com` during install — expect zero packets to toolkit repo host.
- Re-run install: confirm config backup created, skills overwritten cleanly.

## Next Steps / Dependencies
1. Implementation plan (phase-01 edit install.sh, phase-02 new install.command, phase-03 rewrite instruction.txt, phase-04 delete install-skill.sh + README touch-up, phase-05 manual validation).
2. Separate task: `scripts/build-zip.sh` (out of scope here).
3. Optional: CI smoke test that unzips a built artifact and runs `install.sh --dry-run`.

## Open Questions
- Zip top-level folder name — versioned (`openclaw-toolkit-v1/`) or generic (`openclaw-toolkit/`)? Defer to build-zip task.
- Keep `README.txt` inside zip, or strip to minimum (just the two scripts + `skills/`)?
- Any telemetry/analytics needed to know an install happened, given no GitHub ping? Probably no — gateway itself can report if desired later.
