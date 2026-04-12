# openclaw-install-toolkit

One-shot installer that wraps the official [OpenClaw](https://openclaw.ai) setup with an interactive wizard for Telegram + Anthropic credentials.

> **Status:** Gateway installer + skill distribution via `install-skill.sh`. Skills are bundled into this toolkit via git subtree and copied into `~/.openclaw/skills/<name>/` on customer machines; the gateway auto-reloads on the next agent turn (no daemon restart). Shellcheck + E2E smoke on macOS + Ubuntu for both installers.

## Install (one-liner, published URL)

```bash
curl -fsSL https://raw.githubusercontent.com/xuantinfx/openclaw-install-toolkit/main/install.sh | bash -s -- --port 19000
```

## Install (clone)

```bash
git clone https://github.com/xuantinfx/openclaw-install-toolkit.git
cd openclaw-install-toolkit
./install.sh --port 19000
```

After a successful install you can delete the script — OpenClaw handles its own updates.

## Install skills

After `install.sh` completes, install skills bundled with this toolkit into
`~/.openclaw/skills/<name>/`. The gateway picks them up on the next agent turn
— no daemon restart.

```bash
# all bundled skills
curl -fsSL https://raw.githubusercontent.com/xuantinfx/openclaw-install-toolkit/main/install-skill.sh | bash

# one specific skill
curl -fsSL https://raw.githubusercontent.com/xuantinfx/openclaw-install-toolkit/main/install-skill.sh | bash -s -- content-monitor

# see what would be installed; write nothing
curl -fsSL https://raw.githubusercontent.com/xuantinfx/openclaw-install-toolkit/main/install-skill.sh | bash -s -- --dry-run
```

Re-running is idempotent — the target `~/.openclaw/skills/<name>/` is replaced
wholesale, so don't hand-edit files there. The script refuses to run if
`~/.openclaw/` is missing (run `install.sh` first).

## Maintainer: updating a skill

Skills are imported via git subtree (see `scripts/skills.map` for the name →
upstream URL mapping). To refresh from upstream:

```bash
./scripts/sync-skill.sh content-monitor   # or --all
git log -p HEAD                            # review the pulled diff
git push
```

Anything in `skills/*/` on `main` is world-readable once pushed. Review the
diff before pushing; never commit secrets into a subtree-tracked skill.

## Requirements

- macOS or Linux
- Bash 3.2+ (stock macOS works)
- `install.sh` needs `curl` and `jq`
- `install-skill.sh` needs `curl` and `tar`

## Flags

`install.sh`:

| Flag | Default | Purpose |
|---|---|---|
| `--port N` | `18789` | Gateway port written to `~/.openclaw/openclaw.json` |
| `--dry-run` | off | Validate inputs, skip installer + daemon. Useful for CI. |
| `--help` | — | Print usage |

`install-skill.sh`:

| Flag | Default | Purpose |
|---|---|---|
| `[skill ...]` | all | Positional skill names; empty = install every skill in the tarball |
| `--dry-run` | off | Fetch + list what would be installed; write nothing |
| `--help` | — | Print usage |

## Environment overrides

| Var | Scope | Purpose |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | `install.sh` | Skip the token prompt (CI / re-runs) |
| `ANTHROPIC_API_KEY` | `install.sh` | Skip the key prompt |
| `OPENCLAW_INSTALL_URL` | `install.sh` | Override upstream installer URL |
| `OPENCLAW_HOME` | both | Override install dir (default `~/.openclaw`) |
| `TOOLKIT_TARBALL_URL` | `install-skill.sh` | Override toolkit tarball source (forks, private mirrors) |
| `TOOLKIT_ALLOW_INSECURE` | `install-skill.sh` | CI-only: allow `file://` tarballs — never set in prod |

## Security note

Per the installer spec, secrets are inlined in `~/.openclaw/openclaw.json` at mode `0600`. The script refuses to run inside a git worktree. Do not commit or share this file.

Skills distributed via `install-skill.sh` are fetched over HTTPS (TLS 1.2+) from the public toolkit tarball. The installer rejects non-identifier skill names, multi-root tarballs, and any tarball containing symlinks — so a compromised upstream can't path-traverse outside `~/.openclaw/skills/<name>/` or leak files via symlink redirection. `TOOLKIT_ALLOW_INSECURE` relaxes transport checks for local CI fixtures only — never set it in a real install.

## Design rationale

Skill distribution design, trade-offs, and the decision to use git subtree (not submodules, not release-asset tarballs): see [`plans/20260412-1520-skills-subtree-and-installer/brainstorm.md`](plans/20260412-1520-skills-subtree-and-installer/brainstorm.md).
