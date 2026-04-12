# openclaw-toolkit

One-shot installer that wraps the official [OpenClaw](https://openclaw.ai) setup with an interactive wizard for Telegram + Anthropic credentials.

> **Status:** All phases complete — argument parsing, preflight, secret collection, official-installer invocation, config write, daemon start, end-to-end verification (healthz + Telegram + Anthropic), shellcheck, and CI dry-run smoke on macOS + Ubuntu.

## Install (one-liner, published URL)

```bash
curl -fsSL https://raw.githubusercontent.com/<owner>/openclaw-toolkit/main/install.sh | bash -s -- --port 19000
```

## Install (clone)

```bash
git clone https://github.com/<owner>/openclaw-toolkit.git
cd openclaw-toolkit
./install.sh --port 19000
```

After a successful install you can delete the script — OpenClaw handles its own updates.

## Requirements

- macOS or Linux
- `curl`, `jq`
- Bash 3.2+ (stock macOS works)

## Flags

| Flag | Default | Purpose |
|---|---|---|
| `--port N` | `18789` | Gateway port written to `~/.openclaw/openclaw.json` |
| `--dry-run` | off | Validate inputs, skip installer + daemon. Useful for CI. |
| `--help` | — | Print usage |

## Environment overrides

| Var | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Skip the token prompt (CI / re-runs) |
| `ANTHROPIC_API_KEY` | Skip the key prompt |
| `OPENCLAW_INSTALL_URL` | Override upstream installer URL |
| `OPENCLAW_HOME` | Override install dir (default `~/.openclaw`) |

## Security note

Per the installer spec, secrets are inlined in `~/.openclaw/openclaw.json` at mode `0600`. The script refuses to run inside a git worktree. Do not commit or share this file.
