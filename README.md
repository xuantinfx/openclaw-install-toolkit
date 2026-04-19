# openclaw-install-toolkit

Zip-delivered installer that wraps the official [OpenClaw](https://openclaw.ai) setup with an interactive wizard for Telegram + Anthropic credentials, and copies bundled skills into `~/.openclaw/skills/<name>/` in a single step.

> **Status:** Single-script installer. Toolkit is delivered to end users as `openclaw-toolkit.zip` (contains `install.sh`, `install.command`, and `skills/`). Skills are bundled via git subtree and copied on install; the gateway auto-reloads on the next agent turn (no daemon restart). Shellcheck + E2E smoke on macOS + Ubuntu.

> **End-user docs:** see `instruction.txt` for the step-by-step setup guide written for non-technical users.

## Install (end user, zip delivery)

The recipient unzips `openclaw-toolkit.zip` and runs one of:

- **Drag `install.sh` into Terminal** after typing `bash ` — recommended, exec-bit-independent.
- **Double-click `install.command`** — may require one-time Gatekeeper bypass (right-click → Open).

The script prompts for the Telegram bot token + Anthropic API key, runs the official OpenClaw installer, writes `~/.openclaw/openclaw.json` (mode `0600`), starts the gateway, and installs every skill under `./skills/` into `~/.openclaw/skills/`.

Only network call during install is the upstream `openclaw.ai/install-cli.sh` fetch plus Telegram/Anthropic verification pings — no calls to `github.com`.

## Install (developer, from clone)

```bash
git clone https://github.com/xuantinfx/openclaw-install-toolkit.git
cd openclaw-install-toolkit
bash install.sh --port 19000
```

After a successful install you can delete the folder — OpenClaw handles its own updates.

## Maintainer: updating a skill

Skills are imported via git subtree (see `scripts/skills.map` for the name → upstream URL mapping). To refresh from upstream:

```bash
./scripts/sync-skill.sh content-monitor   # or --all
git log -p HEAD                            # review the pulled diff
git push
```

Anything in `skills/*/` on `main` is world-readable once pushed. Review the diff before pushing; never commit secrets into a subtree-tracked skill.

## Requirements

- macOS or Linux
- Bash 3.2+ (stock macOS works)
- `install.sh` needs `curl` and `jq`

## Flags

`install.sh`:

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
| `OPENCLAW_NO_RC_EDIT` | Skip appending the PATH line to `~/.zshrc` / `~/.bash_profile` |

## Security notes

Per the installer spec, secrets are inlined in `~/.openclaw/openclaw.json` at mode `0600`. The script refuses to run inside a git worktree. Do not commit or share this file.

`install_local_skills()` rejects skill directories with non-identifier names, missing `SKILL.md`, or any symlink in the tree — so a tampered zip can't path-traverse outside `~/.openclaw/skills/<name>/` or leak files via symlink redirection. The script does **not** verify zip integrity cryptographically; trust assumptions are documented in the zip-based-install plan.

## Design rationale

Zip delivery design, trade-offs, and the decision to drop per-user GitHub fetches: see [`plans/260419-1825-zip-based-install/plan.md`](plans/260419-1825-zip-based-install/plan.md) and the linked brainstorm report.
