# OpenClaw Installer Wrapper — Brainstorm Summary

**Date:** 2026-04-12
**Status:** Brainstorm complete, awaiting plan phase

---

## Problem Statement

Deliver a single-shot install script that, when run once, leaves the user with a working OpenClaw daemon reachable from their Telegram bot — no manual config editing, no follow-up steps. Script must be disposable: deleting it after install must not break future OpenClaw updates.

## Requirements

### Functional
- Single entrypoint script, idempotent on re-run.
- Interactive prompts (masked where appropriate):
  - `TELEGRAM_BOT_TOKEN`
  - `ANTHROPIC_API_KEY` (required — success criterion below)
- Optional flag: `--port <N>` → becomes `gateway.port` in `openclaw.json`. Default `18789` per OpenClaw docs.
- Model is **hardcoded** to `anthropic/claude-sonnet-4-6` (no provider/model prompts).
- Writes `~/.openclaw/openclaw.json` with **all variables inlined** (per explicit user decision, against OpenClaw's upstream security guidance — see Risks).
- Invokes official installer (`install-cli.sh`) — does not duplicate binary download, PATH, or service-registration logic.
- Starts the OpenClaw daemon and verifies it end-to-end.
- After the script exits successfully, user can immediately message their Telegram bot and get a Claude reply.

### Non-functional
- Idempotent: re-running does not corrupt `openclaw.json`. Detect existing install, offer update-in-place.
- No persistent state outside `~/.openclaw`. Script itself can be `rm`'d safely.
- macOS + Linux support (Windows out of scope — matches OpenClaw's own scope).
- No runtime deps beyond `bash`, `curl`, `jq` (optional), and whatever `install-cli.sh` already requires.

## Final Architecture — Thin Wrapper

```
┌─────────────────────────────────────────────────────────┐
│  install-openclaw.sh (user-facing, disposable)          │
│                                                         │
│  1. Parse flags (--port)                                │
│  2. Prompt: TELEGRAM_BOT_TOKEN (masked)                 │
│  3. Prompt: ANTHROPIC_API_KEY (masked)                  │
│  4. Sanity-check tokens locally (length/prefix)         │
│                                                         │
│  5. curl install-cli.sh | bash   ◄── official installer │
│       • installs binary                                 │
│       • sets up ~/.openclaw layout                      │
│       • registers launchd/systemd service               │
│       • wires auto-update                               │
│                                                         │
│  6. Write ~/.openclaw/openclaw.json (0600)              │
│       • gateway.port        ← --port or 18789           │
│       • channels.telegram.botToken ← inline             │
│       • agents.defaults.model.primary = anthropic/…     │
│       • env.ANTHROPIC_API_KEY ← inline                  │
│                                                         │
│  7. openclaw start  (or restart if already running)     │
│                                                         │
│  8. Verify:                                             │
│       a. poll GET http://127.0.0.1:<port>/healthz → 200 │
│       b. Telegram getMe with bot token → ok:true        │
│       c. Anthropic models.list with API key → 200       │
│                                                         │
│  9. Print: "All green. Message @<botname> on Telegram." │
└─────────────────────────────────────────────────────────┘
```

## Evaluated Approaches

| Option | Effort | Drift risk | Control | Verdict |
|---|---|---|---|---|
| Thin wrapper around `install-cli.sh` + config wizard | Low (~80 LOC) | Low | Medium | **Chosen** |
| Config-only bootstrap (assume openclaw pre-installed) | Very low | None | Low | Rejected — user has to run two commands |
| Full from-scratch installer | High | High | Full | Rejected — duplicates upstream, will rot |

## Config Layout Decisions

### Chosen: inline secrets in `openclaw.json`
Per user decision. `openclaw.json` holds bot token + Anthropic key as literal strings.

### Rejected: `.env` split (OpenClaw upstream convention)
OpenClaw docs explicitly recommend `~/.openclaw/.env` for secrets, with `openclaw.json` referencing `${TELEGRAM_BOT_TOKEN}`. Not chosen.

### Mitigations for the inlined-secrets choice (MUST implement)
- `chmod 0600 ~/.openclaw/openclaw.json` after write.
- Print a one-time warning at install end: *"Secrets are stored in plaintext in ~/.openclaw/openclaw.json. Do not commit or share this file."*
- If `~/.openclaw` is ever inside a git repo, abort install with a loud error. (`git rev-parse --is-inside-work-tree` probe.)
- Document rotation: to change the token, re-run the installer.

## Success Criteria (installer exits 0 only if all pass)

1. `install-cli.sh` exited 0 and `openclaw --version` returns a version string.
2. Gateway `/healthz` on configured port returns HTTP 200 within a 30s poll window.
3. Telegram API `getMe` returns `{"ok":true}` — validates bot token.
4. Anthropic API `GET /v1/models` returns 200 — validates API key.

If any check fails, script prints the specific failure and instructions (regenerate token, check network, etc.) and exits non-zero.

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Plaintext secrets in `openclaw.json` | Token/key exfiltration via backups, screenshots, accidental git commits | `chmod 0600`, git-repo abort check, install-end warning |
| Breaking changes in upstream `install-cli.sh` | Our wrapper stops working silently | Pin to a known-good script URL or verify checksum; re-test on each upstream release |
| `openclaw start` succeeds but agent fails at first message | "Works after install" guarantee violated | Verification step (c) hits Anthropic directly before declaring success |
| User re-runs installer to change token | Duplicate/corrupt JSON | Read-modify-write with JSON parser (`jq`), not string append |
| `--port` collides with another local service | Daemon won't bind | Probe port availability before writing config; prompt to choose another |
| Telegram bot token leaked in shell history if pasted on CLI | Security regression | Use `read -s` (silent read); never accept tokens as CLI args |

## What the Script Will NOT Do (YAGNI)

- Support Windows (matches OpenClaw's own scope).
- Prompt for provider/model — hardcoded to `anthropic/claude-sonnet-4-6`.
- Manage updates — delegated to OpenClaw's own update mechanism.
- Write a `.env` file — all secrets inline per user decision.
- Install multiple bots or multi-agent routing — single default agent only.
- Configure WhatsApp/Discord/Slack channels.

## Resolved Decisions

| Decision | Choice |
|---|---|
| **Distribution** | Both: ship `install.sh` in repo root AND publish same file to a hosted URL. Users can `git clone && ./install.sh` or `curl -fsSL <url> \| bash -s -- --port N`. |
| **Bash floor** | Bash 3.2 — no associative arrays, no `[[ =~ ]]` quirks, no `mapfile`. Runs on stock macOS. |
| **Existing `openclaw.json`** | Backup then overwrite: move to `openclaw.json.bak.<UTC-timestamp>`, write fresh config. Re-runs are safe; old config preserved for diff. |
| **`install-cli.sh` source** | Hardcoded default `https://openclaw.ai/install-cli.sh`, overrideable via `OPENCLAW_INSTALL_URL` env var for testing/mirrors. |

## Implementation Shape

```
install.sh (single file, ~100-120 LOC Bash 3.2)
├── parse_args           — handles --port, --help
├── prompt_secrets       — read -s for TELEGRAM_BOT_TOKEN, ANTHROPIC_API_KEY
├── validate_env         — curl, jq installed; not inside a git worktree under ~/.openclaw
├── run_official_installer
│     OPENCLAW_INSTALL_URL env-overrideable, default https://openclaw.ai/install-cli.sh
├── backup_existing_config  — openclaw.json → openclaw.json.bak.<ts> if present
├── write_config         — jq-built JSON, chmod 0600
├── start_or_restart_daemon
└── verify               — /healthz, Telegram getMe, Anthropic /v1/models
```

## Next Steps

1. `/ck:plan` to produce phased implementation plan with TODOs.
2. Implement `install.sh` in repo root.
3. Test matrix: fresh macOS (stock bash 3.2), Ubuntu 22.04, Alpine-with-bash.
4. CI harness: `TELEGRAM_BOT_TOKEN`/`ANTHROPIC_API_KEY` env vars bypass prompts for automated test runs.
5. Publish to hosted URL once GA-ready.
