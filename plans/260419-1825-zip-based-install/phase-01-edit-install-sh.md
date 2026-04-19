---
phase: 01
status: done
priority: high
effort: M
---

# Phase 01 — Edit install.sh: merge skills logic, drop GitHub fetch

## Overview
Merge `install-skill.sh` logic into `install.sh`. Replace remote tarball fetch with local copy from `$SCRIPT_DIR/skills/`. Add new `install_local_skills()` function wired into `main()` before `on_success`.

## Files
- Modify: `/Users/mac/Documents/AI project x a Kent/openclaw-toolkit/install.sh`
- Read for reference: `/Users/mac/Documents/AI project x a Kent/openclaw-toolkit/install-skill.sh` (port symlink + SKILL.md validation logic)

## Requirements
- Script must detect its own directory via `BASH_SOURCE[0]` (supports both `bash install.sh` invocation and direct `./install.sh`).
- `./skills/` must exist next to the script — fail loudly if missing.
- Each skill subdir must have `SKILL.md` at root — reject corrupt zips.
- Reject symlinks anywhere in skills tree (security — carried over from install-skill.sh).
- Overwrite existing `~/.openclaw/skills/<name>/` (matches current behaviour).
- Preserve Bash 3.2 compatibility — no arrays-with-default, no `[[ ]]` where `[ ]` works.
- Preserve all existing validation, error handling, 0600 config perms, git-worktree refusal.

## Implementation Steps

### 1. Add SCRIPT_DIR resolution near top of file
After the `OPENCLAW_HOME=` line (around line 12-17):
```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```
Quote all downstream uses: `"$SCRIPT_DIR/skills"`.

### 2. Add `install_local_skills()` function
Place between `verify_anthropic()` and `ensure_openclaw_on_path()` (around line 300). Function body:
- Assert `"$SCRIPT_DIR/skills"` exists and is a directory; die with actionable error if not (e.g., "skills/ not found next to install.sh — zip may be corrupt or incomplete").
- Find symlinks in `"$SCRIPT_DIR/skills"` — die if any found (port the `find ... -type l | read -r` pattern from install-skill.sh:111).
- Enumerate subdirs of `"$SCRIPT_DIR/skills"/*/`.
- For each subdir:
  - Validate skill name matches `^[a-z0-9][a-z0-9_-]{0,63}$` (port from install-skill.sh:78-85).
  - Assert `SKILL.md` exists at subdir root; die if missing.
  - `mkdir -p "$OPENCLAW_HOME/skills"`.
  - `rm -rf "$OPENCLAW_HOME/skills/<name>"`.
  - `cp -R "$src" "$dst"`.
  - Log `[skills] installed <name> -> <dst>`.
- Print summary: `[skills] installed N skill(s) into $OPENCLAW_HOME/skills/`.

### 3. Wire into `main()`
In `main()` (around line 373), insert call after `verify_anthropic` and before `on_success`:
```bash
  install_local_skills
```
For `--dry-run` path: also add a dry-run branch inside `install_local_skills` that prints `[dry-run] would install N skill(s) from $SCRIPT_DIR/skills/` and returns without writing.

### 4. Update usage text
In `usage()` (line 27-41), no changes needed — skills are installed automatically now. Optionally add a note mentioning `./skills/` is read from script dir.

### 5. Remove `tar` from dep checks (if present)
Current `install.sh` doesn't check for `tar` — no change needed. `install-skill.sh` checked tar but that's being deleted.

## Todo List
- [ ] Add `SCRIPT_DIR` constant with safe quoting
- [ ] Port skill-name validation regex
- [ ] Port symlink rejection check
- [ ] Implement `install_local_skills()` function
- [ ] Add `--dry-run` branch inside the function
- [ ] Wire call into `main()` before `on_success`
- [ ] Test `bash install.sh --dry-run` manually — confirm skills listed, no copy happens
- [ ] Run `bash -n install.sh` to catch syntax errors
- [ ] Confirm Bash 3.2 compat (no `[[ ]]` in new code where not already used)

## Success Criteria
- `bash install.sh --dry-run` in a path with `./skills/content-monitor/SKILL.md` present → logs "would install 1 skill(s)", exits 0.
- `bash install.sh --dry-run` with missing `./skills/` → fails with clear error.
- `bash install.sh --dry-run` with a symlink planted in `./skills/` → fails with "tarball contains symlinks" equivalent message.
- `bash -n install.sh` — syntax check passes.
- Live end-to-end run (in phase 05) copies skills into `~/.openclaw/skills/`.

## Risks
- `BASH_SOURCE[0]` when piped via `curl | bash` → empty. But this flow no longer supports pipe-to-bash (zip-only). Guard: if `$SCRIPT_DIR` contains `-` (from stdin), die with "run install.sh from unzipped folder, not via pipe".
- Path with spaces — ensure `"$SCRIPT_DIR"` always quoted.
