---
status: completed
created: 2026-04-12
scope: openclaw-installer-wrapper
---

# OpenClaw Installer Wrapper — Implementation Plan

Thin Bash wrapper around `https://openclaw.ai/install-cli.sh` that collects secrets, writes `~/.openclaw/openclaw.json`, starts the daemon, and verifies end-to-end Telegram + Anthropic connectivity.

## Context Links

- Brainstorm: `./brainstorm.md`
- OpenClaw docs (via context7): `/openclaw/openclaw`
- Config shape reference: `~/.openclaw/openclaw.json` JSON5 schema from upstream llms.txt

## Key Locked Decisions

- Single `install.sh` at repo root, Bash 3.2 compatible
- Prompts (masked): `TELEGRAM_BOT_TOKEN`, `ANTHROPIC_API_KEY`
- Flag: `--port N` (default `18789`)
- Hardcoded model: `anthropic/claude-sonnet-4-6`
- Secrets inlined in `openclaw.json` (per user choice; `chmod 0600`, git-worktree abort)
- Existing config → `openclaw.json.bak.<UTC-timestamp>`, overwrite
- Official installer URL overrideable via `OPENCLAW_INSTALL_URL`
- CI bypass: env vars preset → skip prompts
- Target: macOS + Linux only

## Phases

| # | Phase | Status | File |
|---|---|---|---|
| 1 | Scaffold, args, preflight, secrets | completed | [phase-01-scaffold-and-input.md](./phase-01-scaffold-and-input.md) |
| 2 | Run official installer + write config | completed | [phase-02-install-and-config.md](./phase-02-install-and-config.md) |
| 3 | Start daemon + 3-check verification | completed | [phase-03-start-and-verify.md](./phase-03-start-and-verify.md) |
| 4 | Shellcheck, CI smoke, publish URL | completed | [phase-04-test-and-publish.md](./phase-04-test-and-publish.md) |

## Critical Dependencies

- `curl` (bundled on macOS + most Linux)
- `jq` (required; installer fails with a clear message if missing — instructing `brew install jq` / `apt install jq`)
- Official `install-cli.sh` remains reachable at the configured URL
- OpenClaw binary post-install registers its own launchd/systemd unit (per upstream docs)

## Success Criteria (whole plan)

Fresh user on macOS or Ubuntu with zero OpenClaw state runs `./install.sh --port 19000`, enters two tokens, and within ~60 seconds receives a Telegram reply from their bot when they message it. Exit code 0. Secrets never logged.

## Out of Scope (YAGNI)

- Windows support
- Non-Anthropic providers
- `.env` secret split
- Multi-agent routing, WhatsApp/Discord channels
- Custom skill/plugin config
- Auto-update (handled by upstream)
