# Phase 1 — Subtree Bootstrap + Maintainer Helper

## Overview
- **Priority:** P0 (blocks all later phases)
- **Status:** completed (2026-04-13)
- **Depends on:** SSH access to `hoangnhatfe/content-monitor`

One-time subtree bootstrap of `content-monitor` into this repo, plus an optional maintainer script that wraps the weekly pull command.

## Key Insights

- `git subtree` is bundled with git ≥ 1.7.11 — no install needed.
- `--squash` flattens upstream history into a single merge commit — smaller diffs, easier rollback, no leaking upstream author metadata.
- Subtree's quirk: the `--prefix` path must be relative with NO leading slash and NO trailing slash.
- `git subtree add` creates commits on current branch — need a clean working tree first.

## Requirements

### Functional
- `skills/content-monitor/` exists in toolkit root after phase, containing `SKILL.md` + any supporting files from `content-monitor/main`.
- Maintainer can run one command to refresh from upstream.
- Optional: `scripts/sync-skill.sh <name>` looks up upstream URL from a map file and runs the correct subtree pull.

### Non-functional
- No submodule files (`.gitmodules` stays absent).
- Squashed commits — one commit per sync.

## Architecture

```
openclaw-install-toolkit/
├── skills/
│   └── content-monitor/              ← subtree (regular files)
│       └── SKILL.md
└── scripts/                          ← maintainer-only (optional)
    ├── sync-skill.sh                 ← wrapper around git subtree
    └── skills.map                    ← name -> git URL lookup
```

## Related Code Files

### Create
- `skills/content-monitor/` (populated by `git subtree add`, not hand-written)
- `scripts/sync-skill.sh`
- `scripts/skills.map`

### Modify
- None in this phase

## Implementation Steps

1. Verify clean git state: `git status` shows no uncommitted changes.
2. One-time subtree add:
   ```bash
   git subtree add --prefix=skills/content-monitor \
     git@github.com:hoangnhatfe/content-monitor.git main --squash \
     -m "feat: add content-monitor skill via subtree"
   ```
3. Verify: `ls skills/content-monitor/` shows `SKILL.md`.
4. Push to origin: `git push`.
5. Write `scripts/skills.map` (simple `name<TAB>url` format):
   ```
   content-monitor	git@github.com:hoangnhatfe/content-monitor.git	main
   ```
6. Write `scripts/sync-skill.sh`:
   - Usage: `./scripts/sync-skill.sh <name>` or `./scripts/sync-skill.sh --all`
   - Reads `skills.map`, runs `git subtree pull --prefix=skills/<name> <url> <branch> --squash` for each matching row
   - `set -euo pipefail`, shellcheck clean, Bash 3.2 compatible
7. `chmod +x scripts/sync-skill.sh`
8. Commit scripts, push.

## Todo List
- [x] Verify SSH access to `hoangnhatfe/content-monitor`
- [x] `git subtree add` for content-monitor
- [x] Push subtree commit
- [x] Write `scripts/skills.map`
- [x] Write `scripts/sync-skill.sh`
- [x] Commit + push helpers

## Success Criteria
- `skills/content-monitor/SKILL.md` exists on `main` upstream.
- `./scripts/sync-skill.sh content-monitor` runs a subtree pull cleanly on an up-to-date tree (no-op if nothing changed upstream).
- No `.gitmodules` file exists.

## Risk Assessment
- **SSH auth failure**: if SSH key isn't registered on `hoangnhatfe/content-monitor`, `subtree add` fails. Fix: ensure read access before starting.
- **Upstream has no `SKILL.md` at root**: skill may be in a subdir. Fix: use `--prefix=skills/content-monitor` only if `SKILL.md` is at content-monitor's root; otherwise plan for a subdir-mapped subtree or post-copy step. Verify before running.
- **Forgotten `git push`**: subtree add creates local commits only. Push immediately.

## Security
- Reminder in `scripts/sync-skill.sh` output: "files you pull become world-readable once pushed to public toolkit main — review diff before pushing."
- No secrets or credentials in `skills.map` (just URLs).

## Next Steps
→ Phase 2 (install-skill.sh can now copy real files).
