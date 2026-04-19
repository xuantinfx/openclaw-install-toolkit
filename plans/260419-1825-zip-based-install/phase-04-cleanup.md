---
phase: 04
status: done
priority: medium
effort: S
---

# Phase 04 — Cleanup: delete install-skill.sh, refresh README

## Overview
Remove the now-redundant `install-skill.sh`. Touch up `README.md` so it no longer advertises the old curl-based two-step flow.

## Files
- Delete: `/Users/mac/Documents/AI project x a Kent/openclaw-toolkit/install-skill.sh`
- Modify: `/Users/mac/Documents/AI project x a Kent/openclaw-toolkit/README.md`

## Requirements
- `install-skill.sh` only deleted AFTER phase 01 has successfully merged its logic into `install.sh`.
- `README.md` should reflect zip-based delivery. If README doc maintainer tone is technical/developer-focused (not end-user), keep technical voice there — `instruction.txt` is the end-user doc.
- No dangling references to `install-skill.sh` anywhere in repo (`git grep`).

## Implementation Steps

### 1. Verify phase 01 merged skills logic
Pre-check: `grep -n 'install_local_skills' install.sh` → must return matches.

### 2. Delete install-skill.sh
```bash
git rm install-skill.sh
```

### 3. Update README.md
Read current content first. Likely changes:
- Remove any "Install skills" section pointing at `install-skill.sh`.
- Replace curl quick-start commands with "Download the toolkit zip delivered to you and run `install.sh`".
- Keep developer-facing sections (repo structure, dev notes) as-is.
- Add one-liner: "End-user docs: see `instruction.txt`".

### 4. Grep for dangling references
```bash
git grep -n 'install-skill' .
git grep -n 'raw.githubusercontent.com/xuantinfx/openclaw-install-toolkit' .
```
Both should return zero hits after this phase. Acceptable: references in `plans/` (historical) and `.git/` are fine; fix only live repo files.

## Todo List
- [ ] Confirm `install_local_skills()` exists in install.sh
- [ ] `git rm install-skill.sh`
- [ ] Read current README.md
- [ ] Rewrite quick-start + skills sections in README.md
- [ ] Run `git grep install-skill` — fix any live references
- [ ] Run `git grep raw.githubusercontent.com/xuantinfx` — fix any live references

## Success Criteria
- `install-skill.sh` no longer present in repo.
- No live references to `install-skill.sh` or the old GitHub curl URLs outside `plans/`.
- `README.md` describes zip-based flow accurately.

## Risks
- Deleting install-skill.sh before phase 01 completes = broken HEAD. Gate this phase behind phase 01 merge.
- README may be consumed by the install-cli.sh upstream somehow — unlikely but worth a quick skim before edit.
