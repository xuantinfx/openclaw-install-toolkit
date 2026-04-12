# Phase 1 — Scaffold, Args, Preflight, Secrets

## Overview
- **Priority:** P0 (foundation)
- **Status:** completed
- **Depends on:** none
- Lay down `install.sh` skeleton: strict mode, arg parsing, environment detection, dependency checks, secret collection with format validation and env-var bypass.

## Key Insights
- Bash 3.2 is stock on macOS. Avoid `declare -A`, `mapfile`, `[[ =~ ]]` Bash-4-specific flags. Stick to POSIX-ish constructs + explicit `grep -E` for regex.
- Never echo secrets. Use `read -s` and unset variables at script exit via `trap`.
- Env-var bypass is the *only* way to make the script CI-testable without TTY.

## Requirements

### Functional
- `install.sh [--port N] [--help]`
- If `$TELEGRAM_BOT_TOKEN` set and non-empty → skip token prompt. Same for `$ANTHROPIC_API_KEY`.
- Validate token formats before touching network:
  - Telegram: `^[0-9]{5,}:[A-Za-z0-9_-]{30,}$`
  - Anthropic: starts with `sk-ant-` and length > 20
- Abort with actionable error if `curl` or `jq` is missing.
- Abort if `$HOME/.openclaw` is inside a git worktree (prevents accidental secret commit).
- Detect OS: only `Darwin` and `Linux` accepted; fail loudly otherwise.

### Non-functional
- Script passes `shellcheck -s bash` with zero warnings at default severity.
- `set -euo pipefail` + `IFS=$'\n\t'`.
- `trap cleanup EXIT` unsets secret vars.

## Architecture
```
install.sh
├── main()
│   ├── parse_args "$@"        # --port, --help
│   ├── preflight()            # OS, deps, git-worktree check
│   ├── collect_secrets()      # env-first, then prompt
│   ├── validate_secrets()     # regex
│   └── (exits here in phase-01 stub; phases 2-3 fill in)
└── cleanup()                  # unset TELEGRAM_BOT_TOKEN ANTHROPIC_API_KEY
```

## Related Code Files

### Create
- `/Users/mac/Documents/funny-with-code/openclaw-toolkit/install.sh`
- `/Users/mac/Documents/funny-with-code/openclaw-toolkit/README.md` (minimal — usage + one-liner)

### Modify
- none (fresh repo)

## Implementation Steps

1. Create `install.sh`. Shebang `#!/usr/bin/env bash`, then `set -euo pipefail; IFS=$'\n\t'`.
2. Define constants: `OPENCLAW_HOME="$HOME/.openclaw"`, `DEFAULT_PORT=18789`, `DEFAULT_INSTALL_URL="https://openclaw.ai/install-cli.sh"`, `MODEL="anthropic/claude-sonnet-4-6"`.
3. Implement `usage()` and `die()` helpers. `die` prints to stderr and exits 1.
4. Implement `parse_args`: loop over `$@`, handle `--port=<n>` and `--port <n>` and `--help`. Reject unknown flags with `usage`. Validate port is integer 1-65535.
5. Implement `preflight`:
   - `uname -s` must be `Darwin` or `Linux`.
   - `command -v curl >/dev/null` and `command -v jq >/dev/null` or `die` with install hint per OS.
   - If `-d "$OPENCLAW_HOME"`: run `(cd "$OPENCLAW_HOME" && git rev-parse --is-inside-work-tree 2>/dev/null)` — if succeeds, `die "refusing to write secrets inside a git worktree"`.
6. Implement `collect_secrets`:
   - If `-z "${TELEGRAM_BOT_TOKEN:-}"`: `printf 'Telegram bot token: '; read -rs TELEGRAM_BOT_TOKEN; echo`.
   - Same pattern for `ANTHROPIC_API_KEY`.
   - Export both for later phases.
7. Implement `validate_secrets`: grep-based regex check; `die` with "invalid format for X" on fail.
8. Register `cleanup() { unset TELEGRAM_BOT_TOKEN ANTHROPIC_API_KEY; }` and `trap cleanup EXIT`.
9. Make executable: `chmod +x install.sh`.
10. Shellcheck: `shellcheck install.sh`. Zero issues.
11. Manual smoke: run `./install.sh --help`, `./install.sh --port abc` (should fail), `./install.sh --port 19000` (prompts → aborts at phase-02 stub since we haven't implemented it yet).
12. Apply code review tweaks: drop premature `export` of secret vars, tighten git-worktree probe to walk up to nearest existing ancestor dir.

## Todo List
- [x] `install.sh` skeleton with strict mode and trap
- [x] `parse_args` with `--port` and `--help`
- [x] `preflight` with OS + deps + git-worktree checks
- [x] `collect_secrets` with env bypass
- [x] `validate_secrets` regex checks
- [x] `README.md` — usage and one-liner
- [x] shellcheck passes

## Success Criteria
- `./install.sh --help` prints usage, exits 0.
- `./install.sh --port 70000` exits 1 with clear error.
- `TELEGRAM_BOT_TOKEN=bad ANTHROPIC_API_KEY=sk-ant-xyzxyzxyzxyzxyzxyzxyzxyz ./install.sh` exits 1 with "invalid format" on the bad token.
- Shellcheck clean.

## Risks
- Bash 3.2 quirks around `read -s` on macOS: ensure we `echo` after the read to avoid a cursor stuck on the prompt line.
- User types bot token into the shell history by accident — mitigated by disallowing tokens as CLI args.

## Security
- Secrets never appear in process list: `read -s`, no CLI args, no `export -p` dumps in debug mode.
- `trap cleanup EXIT` unsets on any exit path (success, error, user ^C).
- No `set -x` left on in final script.

## Next Steps
- Phase 2: invoke official installer, write `openclaw.json`.
