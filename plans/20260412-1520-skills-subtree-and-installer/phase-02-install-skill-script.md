# Phase 2 — `install-skill.sh` (Customer Skill Installer)

## Overview
- **Priority:** P0
- **Status:** completed (2026-04-13)
- **Depends on:** phase-01

Customer-facing script that fetches the toolkit tarball, extracts `skills/<name>/` directories, and copies them to `~/.openclaw/skills/`. Multi-skill from day one. Bash 3.2 + shellcheck clean.

## Key Insights

- GitHub tarball URL pattern: `https://github.com/<owner>/<repo>/archive/refs/heads/<branch>.tar.gz` — unauthenticated, supports `curl -fsSL`.
- Extracted tarball top-level dir is `<repo>-<branch>/` (e.g., `openclaw-install-toolkit-main/`), so we enumerate `$tmpdir/*/skills/*/`.
- Gateway autoreloads on next agent turn — no daemon restart needed (per OpenClaw docs: `skills.load.watch: true` default).
- Copy strategy: `rm -rf` target + fresh `cp -R` (idempotent; no stale files). `cp -R` preserves exec bits — matters for `scripts/` inside skills.
- Target path: `~/.openclaw/skills/<name>/` — per OpenClaw FAQ this is the user-level shared-across-agents location. Skill is picked up by gateway on next agent turn (no restart, `skills.load.watch` default true).
- Validation: require `SKILL.md` at the root of each copied skill directory — without it the skill is invalid per OpenClaw spec.

## Requirements

### Functional
- `install-skill.sh` (no args) → install ALL skills found in `skills/*/` in the tarball.
- `install-skill.sh content-monitor foo` → install only named skills; fail fast on missing.
- `--dry-run` flag → fetch tarball, print what would be installed, don't write.
- `--help` / `-h` → usage.
- Require `~/.openclaw/` to exist → otherwise: `die "run install.sh first"`.
- Always overwrite (`rm -rf` then `cp -R`) — simpler than diff/merge.

### Non-functional
- Shellcheck clean (zero warnings).
- Bash 3.2 compatible.
- `set -euo pipefail`, `IFS=$'\n\t'`.
- Works under `curl | bash`.
- `mktemp` cleanup via trap.

## Architecture

```
install-skill.sh
├── parse_args
├── preflight          (curl, tar, ~/.openclaw exists)
├── fetch_tarball      (curl -fsSL .../main.tar.gz | tar -xz -C $tmpdir)
├── enumerate_skills   (args OR `ls $tmpdir/*/skills/`)
├── for each:
│   ├── verify src dir exists
│   ├── rm -rf ~/.openclaw/skills/<name>
│   └── cp -R src ~/.openclaw/skills/<name>
└── summarize
```

## Related Code Files

### Create
- `install-skill.sh` (repo root, `chmod 0755`)

### Modify
- None this phase

## Implementation Steps

1. Script skeleton with `set -euo pipefail`, `trap` for tmpdir cleanup, `die()` helper, `usage()`.
2. `parse_args`:
   - Positional args collect into `SKILLS=()` (Bash 3.2: use string + `$IFS` split since arrays vary).
   - Actually Bash 3.2 DOES support arrays — just not associative arrays. Regular arrays are fine.
   - Flags: `--dry-run`, `--help`, `-h`. Unknown → usage + die.
3. `preflight`:
   - `require_cmd curl` / `require_cmd tar`.
   - Check `~/.openclaw/` is a dir → else die with clear message.
4. `fetch_tarball`:
   - `TOOLKIT_TARBALL_URL="${TOOLKIT_TARBALL_URL:-https://github.com/xuantinfx/openclaw-install-toolkit/archive/refs/heads/main.tar.gz}"` (env override for testing).
   - `tmpdir=$(mktemp -d)`; set trap to rm on EXIT.
   - `curl -fsSL --proto '=https' --tlsv1.2 --max-time 60 "$TOOLKIT_TARBALL_URL" | tar -xz -C "$tmpdir"`.
   - Locate extracted root: `tarball_root=$(find "$tmpdir" -maxdepth 1 -type d -name '*-*' | head -1)` — single dir under tmpdir.
5. `enumerate_skills`:
   - If SKILLS empty: populate from `ls "$tarball_root/skills"`.
   - Else: each named skill must resolve to `$tarball_root/skills/<name>/`.
6. For each skill:
   - `src="$tarball_root/skills/$skill"`; `[ -d "$src" ] || die "skill not in toolkit: $skill"`.
   - `[ -f "$src/SKILL.md" ]` → **required** per OpenClaw skill spec; die with clear error if missing (indicates corrupt/wrong-shape skill dir).
   - If `$DRY_RUN`: `printf '[dry-run] would install %s\n' "$skill" >&2`; skip copy.
   - Else: `dst="$HOME/.openclaw/skills/$skill"`; `rm -rf "$dst"`; `mkdir -p "$(dirname "$dst")"`; `cp -R "$src" "$dst"`.
7. Summary:
   - Print installed skills + gateway auto-reload note.
   - Exit 0.

## Todo List
- [x] `install-skill.sh` skeleton (set -euo, trap, die, usage)
- [x] `parse_args` with SKILLS array + flags
- [x] `preflight` (curl/tar/~/.openclaw)
- [x] `fetch_tarball` with env-overrideable URL
- [x] `enumerate_skills` (args-or-glob)
- [x] copy loop with `--dry-run` gate
- [x] summary + exit 0
- [x] `chmod 0755 install-skill.sh`
- [x] smoke test (dry-run + install + idempotent re-run + bogus-skill against live tarball)

## Success Criteria
- `./install-skill.sh --dry-run` lists `content-monitor` (after phase 1).
- `./install-skill.sh` on a machine with openclaw installed ends with `~/.openclaw/skills/content-monitor/SKILL.md` present.
- Running it a second time is idempotent (overwrites cleanly, exit 0).
- `./install-skill.sh bogus-skill` exits non-zero with a clear error.

## Risk Assessment
- **Tarball URL rate limits**: `github.com/.../archive/...` has soft limits. Acceptable for installer traffic volumes; flag if adoption grows.
- **Large tarballs**: plans/ + reports/ bulk the download. ~100KB now, not a concern; could switch to release assets later.
- **Bash array compatibility**: test on stock macOS `/bin/bash` 3.2 specifically.
- **Customer disk state**: if user has manually edited `~/.openclaw/skills/content-monitor/`, we silently overwrite. Acceptable per spec. Document in help text.

## Security
- Use `curl --proto '=https' --tlsv1.2` — same posture as `install.sh`.
- No secrets handled by this script.
- Reminder: Tarball is public; anyone can inspect. No confidential data should ever be committed to `skills/*/`.

## Next Steps
→ Phase 3 (CI coverage).
