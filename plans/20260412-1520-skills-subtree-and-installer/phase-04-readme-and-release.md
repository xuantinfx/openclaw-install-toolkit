# Phase 4 — README + Release

## Overview
- **Priority:** P1
- **Status:** completed (2026-04-13)
- **Depends on:** phase-03

Document the new customer one-liner and the maintainer workflow in README. Ship the final commits.

## Requirements

### Functional
- README gets two new sections:
  1. **Install skills (customer)** — one-liner for `install-skill.sh`.
  2. **Skill management (maintainer)** — brief note on `scripts/sync-skill.sh` + weekly pull cadence.
- Link to `plans/20260412-1520-skills-subtree-and-installer/brainstorm.md` for full design rationale.
- Clarify that skills auto-reload (no daemon restart on customer side).

### Non-functional
- Copy-pasteable one-liners.
- No `<placeholder>` strings remain.

## Architecture

README additions (sketch):

```markdown
## Install skills

After `install.sh` completes, install bundled skills:

\`\`\`bash
# all bundled skills
curl -fsSL https://raw.githubusercontent.com/xuantinfx/openclaw-install-toolkit/main/install-skill.sh | bash

# specific skill(s)
curl -fsSL https://raw.githubusercontent.com/xuantinfx/openclaw-install-toolkit/main/install-skill.sh | bash -s -- content-monitor
\`\`\`

Skills land at `~/.openclaw/skills/<name>/`. The gateway auto-reloads on next agent turn.

## Maintainer: updating a skill

Skills are imported via git subtree. To refresh from upstream:

\`\`\`bash
./scripts/sync-skill.sh content-monitor
git push
\`\`\`

Review the diff before pushing — anything in a skill folder on `main` is public.
```

## Related Code Files

### Modify
- `README.md`

## Implementation Steps

1. Add "Install skills" section after the existing "Install (clone)" section.
2. Add "Maintainer: updating a skill" section (below Security note or in a separate "Contributing" section).
3. Update status blurb at top to mention skill distribution.
4. Commit with message: `docs: install-skill one-liner + maintainer subtree workflow`.
5. Push.
6. Manual end-to-end verification on a fresh machine (or second directory):
   - `rm -rf ~/.openclaw/skills/content-monitor` (if exists).
   - Run customer one-liner from the raw URL.
   - Confirm `~/.openclaw/skills/content-monitor/SKILL.md` exists.
   - Confirm gateway still healthy: `curl http://127.0.0.1:19000/healthz` → `{"ok":true,"status":"live"}`.

## Todo List
- [x] README: "Install skills" section
- [x] README: "Maintainer: updating a skill" section
- [x] README: update top-of-file status blurb
- [x] README: security note extended; design-rationale link to brainstorm.md
- [x] Commit + push (commit 02bed85)
- [x] Manual customer-side verification (curl|bash one-liner run verbatim, SKILL.md landed, dry-run wrote nothing)

## Success Criteria
- README one-liners work when pasted verbatim.
- No `<owner>` / `<placeholder>` text remains.
- End-to-end manual test on a clean directory passes.

## Risk Assessment
- **Stale URL**: one-liner URL locked to `main` branch. If you ever rename the default branch, update README. Low risk.
- **Customer runs install-skill.sh before install.sh**: we die early with a clear message (phase 2). README should mention install.sh must run first.

## Security
- Remind (again) in README: anything in `skills/*/` is world-readable once pushed. Never commit secrets upstream in content-monitor.

## Next Steps
- Consider CI auto-sync PR workflow if manual cadence slips (deferred).
- Consider signed skill bundles if adoption grows (deferred).
