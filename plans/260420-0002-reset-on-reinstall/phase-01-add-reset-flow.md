# Phase 01 — Add reset-on-reinstall flow to install.sh

## Overview
- **Priority:** High
- **Status:** done (review-hardened)
- **Effort:** ~1-2h implementation + ~30min docs

Detect existing install via `$OPENCLAW_HOME/openclaw.json`. Under TTY: prompt y/N (default N). Under `curl|bash`: skip silently with notice. Two flags (`--reset`, `--keep-data`) override prompt. On confirmation: `openclaw reset --scope full --yes --non-interactive`. Non-zero exit → abort.

## Key Insights
- `openclaw reset` is idempotent on the server side, but requires the CLI binary. If binary missing → warn + skip (don't try `rm -rf` fallback).
- `prompt_secret()` already has the `/dev/tty` reader pattern. Reuse that style for the y/N prompt — don't touch stdin.
- Detection must run AFTER `parse_args` (to honor flags) but BEFORE `preflight` (wipe first, then check deps — preflight doesn't need prior state).
- Actually: run AFTER `preflight` so we know `curl` + `jq` are present, and AFTER `collect_secrets`/`validate_secrets` so we don't wipe then fail on bad token. Order: parse → preflight → collect → validate → **reset gate** → upstream installer → config → daemon.
- **Exception:** if `--reset` explicitly passed, run reset BEFORE `collect_secrets` so the user isn't prompted for secrets we're about to discard? No — user running `--reset` already intends to reinstall, will need secrets anyway. Keep single insertion point for simplicity.

## Requirements

### Functional
1. `install.sh` accepts `--reset` and `--keep-data` flags. Mutually exclusive → usage error.
2. `install.sh` accepts env var `OPENCLAW_RESET=1` as equivalent of `--reset` (for CI / scripted re-runs). `OPENCLAW_KEEP_DATA=1` mirrors `--keep-data`.
3. Detection: `[ -f "$OPENCLAW_HOME/openclaw.json" ]`. Directory-only or `bin/`-only does NOT trigger prompt.
4. Decision table:
   | flag/env | TTY available | behavior |
   |---|---|---|
   | `--reset` or `OPENCLAW_RESET=1` | any | run reset, no prompt |
   | `--keep-data` or `OPENCLAW_KEEP_DATA=1` | any | skip reset, no prompt |
   | neither | yes | prompt `[warn] ... wipe? [y/N]` → default N |
   | neither | no | skip reset, print notice |
5. Wipe command: `openclaw reset --scope full --yes --non-interactive`.
6. If `openclaw` not on PATH:
   - With `--reset`: abort with "cannot reset: openclaw binary not found at expected locations (tried: PATH, $OPENCLAW_HOME/bin, npm prefix)".
   - Without `--reset` (prompted path): emit warning "config present but binary missing — skipping reset", continue install.
7. If `openclaw reset` exits non-zero: abort with exit code + suggestion "try: openclaw uninstall --all --yes --non-interactive && rerun install.sh".
8. `--dry-run` honors the same decision table but does NOT execute `openclaw reset` — logs what it would do.

### Non-Functional
- Bash 3.2 compatible (no associative arrays, no `mapfile`).
- Zero change to behavior for first-time installs (no `openclaw.json` present).
- Prompt must read from `/dev/tty` (same pattern as `prompt_secret`) so it works under `bash <(curl ...)` when a controlling TTY is present.

## Architecture

### New function: `maybe_reset_existing_install()`
Location: after `validate_secrets`, before `run_official_installer` in `main()`.

Pseudo:
```bash
maybe_reset_existing_install() {
  local cfg="$OPENCLAW_HOME/openclaw.json"
  [ -f "$cfg" ] || return 0   # fresh install, nothing to do

  # Resolve --reset / --keep-data / env vars into a decision.
  local decision=""   # "reset" | "skip" | "ask"
  if [ "$RESET" -eq 1 ] && [ "$KEEP_DATA" -eq 1 ]; then
    die "--reset and --keep-data are mutually exclusive"
  fi
  [ "$RESET" -eq 1 ] && decision="reset"
  [ "$KEEP_DATA" -eq 1 ] && decision="skip"
  [ -z "$decision" ] && decision="ask"

  if [ "$decision" = "ask" ]; then
    if [ -r /dev/tty ] && [ -w /dev/tty ]; then
      printf '[warn] existing OpenClaw install detected at %s\n' "$OPENCLAW_HOME" >/dev/tty
      printf '[warn] wipe config, skills, credentials, sessions before reinstalling? [y/N]: ' >/dev/tty
      local ans
      IFS= read -r ans </dev/tty
      printf '\n' >/dev/tty
      case "$ans" in
        y|Y|yes|YES) decision="reset" ;;
        *)           decision="skip"  ;;
      esac
    else
      printf '[info] existing install detected at %s — skipping wipe (no TTY). Pass --reset to force.\n' "$OPENCLAW_HOME" >&2
      decision="skip"
    fi
  fi

  if [ "$decision" = "skip" ]; then
    printf '[info] keeping existing data at %s\n' "$OPENCLAW_HOME" >&2
    return 0
  fi

  # decision=reset. Locate openclaw binary (same search as run_official_installer).
  if ! command -v openclaw >/dev/null 2>&1; then
    local prefix cand
    prefix="$(npm prefix -g 2>/dev/null || true)"
    for cand in \
      "$OPENCLAW_HOME/bin" \
      "${prefix:+$prefix/bin}" \
      "$HOME/.npm-global/bin" \
      "$HOME/.local/bin" \
      "/opt/homebrew/bin" \
      "/usr/local/bin"; do
      if [ -n "$cand" ] && [ -x "$cand/openclaw" ]; then
        PATH="$cand:$PATH"; export PATH
        hash -r 2>/dev/null || true
        break
      fi
    done
  fi

  if ! command -v openclaw >/dev/null 2>&1; then
    if [ "$RESET" -eq 1 ]; then
      die "cannot reset: openclaw binary not found (config at $cfg is orphaned). Run: rm -rf $OPENCLAW_HOME, then re-run install.sh"
    fi
    printf '[warn] config at %s but no openclaw binary on PATH — skipping reset\n' "$cfg" >&2
    return 0
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] would run: openclaw reset --scope full --yes --non-interactive\n' >&2
    return 0
  fi

  printf '[reset] running openclaw reset --scope full --yes --non-interactive\n' >&2
  if ! openclaw reset --scope full --yes --non-interactive; then
    die "openclaw reset failed. Manual cleanup: openclaw uninstall --all --yes --non-interactive && rm -rf $OPENCLAW_HOME, then re-run install.sh"
  fi
  printf '[reset] done\n' >&2
}
```

### Changes to existing functions

- `parse_args()`:
  - Add `--reset` → `RESET=1`
  - Add `--keep-data` → `KEEP_DATA=1`
  - Mutually-exclusive check after loop
- Globals at top of file:
  - `RESET=0`
  - `KEEP_DATA=0`
  - Seed from env: `RESET="${OPENCLAW_RESET:-0}"`, `KEEP_DATA="${OPENCLAW_KEEP_DATA:-0}"`
- `usage()`:
  - Document both flags + both env vars
- `main()`:
  - Insert `maybe_reset_existing_install` between `validate_secrets` and the `if [ "$DRY_RUN" -eq 1 ]` branch for the installer call

## Related Code Files

**Modify:**
- `install.sh` — add function, flags, usage text, call site in `main()`
- `README.md` — document `--reset` / `--keep-data` in the flags table + env var table
- `instruction.txt` — one-line note for end users: "If reinstalling, the script will ask whether to wipe old data — press Enter to keep it."

**Create:** none
**Delete:** none

## Implementation Steps

1. Add globals + env seeding for `RESET` and `KEEP_DATA` (near existing `DRY_RUN=0`).
2. Add cases to `parse_args()` loop for `--reset` and `--keep-data`.
3. Add mutually-exclusive validation after the `while` loop in `parse_args()`.
4. Update `usage()` heredoc with new flags + env vars.
5. Implement `maybe_reset_existing_install()` per pseudo above.
6. Wire into `main()` after `validate_secrets`.
7. `shellcheck install.sh` — fix any warnings introduced.
8. Smoke-test `bash install.sh --dry-run` on a machine with `~/.openclaw/openclaw.json` present — verify prompt fires, default N behaves identically to today.
9. Update `README.md` flags table + env overrides table.
10. Update `instruction.txt` with one-line note.

## Todo List
- [ ] Add `RESET` + `KEEP_DATA` globals with env seeding
- [ ] Parse `--reset` / `--keep-data` flags
- [ ] Enforce mutual exclusivity
- [ ] Update `usage()` text
- [ ] Implement `maybe_reset_existing_install()`
- [ ] Insert call in `main()` after `validate_secrets`
- [ ] Run shellcheck, fix warnings
- [ ] Smoke test `--dry-run` path with + without pre-existing config
- [ ] Update `README.md` (flags + env tables)
- [ ] Update `instruction.txt` (one-line note)

## Success Criteria
- `shellcheck install.sh` passes without new warnings.
- `bash install.sh --dry-run --reset` with `~/.openclaw/openclaw.json` present logs `[dry-run] would run: openclaw reset --scope full --yes --non-interactive` and does not execute reset.
- `bash install.sh --dry-run --reset --keep-data` exits with usage error about mutual exclusivity.
- `OPENCLAW_RESET=1 bash install.sh --dry-run` behaves identically to `bash install.sh --dry-run --reset`.
- `bash install.sh --dry-run` with config present + no TTY (`</dev/null`) logs the skip notice and returns 0.
- First-run install (no `~/.openclaw/openclaw.json`) path is byte-identical to current behavior (no prompt, no log line about reset).

## Risk Assessment
- **Wrong insertion point in `main()`.** Running reset AFTER upstream installer would wipe the freshly-installed binary+config → corrupts install. Mitigation: explicit ordering in plan (reset before `run_official_installer`). Verify in review.
- **Prompt default flip.** Changing default from N to Y in a future edit destroys user data silently. Mitigation: add a comment in the function noting "default N is load-bearing — never change without user-facing announcement".
- **`openclaw reset` hang under CI.** If CLI blocks on stdin without `--yes`, install hangs forever. Mitigation: command is `reset --scope full --yes --non-interactive` — all three flags required per CLI docs; verified via context7 lookup.

## Security Considerations
- Reset wipes credentials (per upstream docs for `--scope full`). Re-prompt logic already in `install.sh` handles this.
- No new network calls, no new file creations outside `$OPENCLAW_HOME`.
- Prompt reads from `/dev/tty` — consistent with existing `prompt_secret()` pattern; no stdin hijack risk.

## Next Steps
- Phase 02: manual validation matrix.
