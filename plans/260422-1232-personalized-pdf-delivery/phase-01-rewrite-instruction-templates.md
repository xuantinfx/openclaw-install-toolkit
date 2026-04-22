---
phase: 01
status: completed
effort: medium
---

# Phase 01 — Rewrite instruction content as Markdown templates

## Context
Current `instruction.txt` and `instruction-multi-user.txt` use ASCII banners (`====`, `----`) and manual indentation. For PDF render we need proper Markdown headings, lists, and code fences. This phase rewrites content verbatim (semantic preservation), only the structure changes.

## Key Insights
- ASCII banners → MD headings: `====` line → `#`, `----` line → `##`. Deliberate mapping, not clever parsing.
- Numbered steps (`1. 2. 3.`) already legal MD — keep as-is.
- Inline commands currently displayed in indented blocks → convert to fenced code blocks (` ``` `).
- URLs (e.g. `https://console.anthropic.com`) stay as bare URLs — Markdown auto-links them in md-to-pdf.
- No template vars in the instruction body itself — vars live ONLY in the legal header (phase 02). Instruction body is client-agnostic.

## Requirements
- `instruction.md.tmpl` is a faithful MD rewrite of `instruction.txt`. Every step, warning, and URL preserved.
- `instruction-multi-user.md.tmpl` is a faithful MD rewrite of `instruction-multi-user.txt`.
- No `{{...}}` placeholders in these two files (legal header handles all personalization).
- Old `.txt` files deleted in the same commit to prevent drift.

## Related Code Files
- **Read & rewrite**: `instruction.txt`, `instruction-multi-user.txt`
- **Create**: `instruction.md.tmpl`, `instruction-multi-user.md.tmpl`
- **Delete**: `instruction.txt`, `instruction-multi-user.txt`
- **Leave untouched**: `README.md` (bundle-level, already MD)

## Implementation Steps
1. Read full `instruction.txt`; map section headers:
   - Document title (`==== line`) → `# How to set up your OpenClaw AI assistant on Telegram`
   - Section headers (`---- line`) → `## STEP N — Title` / `## BEFORE YOU START` etc.
2. Convert indented command blocks (e.g. 4-space indented `curl -fsSL ...`) to fenced ``` ```bash blocks ```.
3. Convert bullet lists (`  - `) to standard MD (`- `).
4. Convert numbered lists (`  1. `) to standard MD (`1. `).
5. Preserve inline emphasis where present (bold section callouts, code-style tokens).
6. Leave line length ≤ 100 where it flows naturally; no hard wrapping needed — MD→PDF reflows.
7. Repeat steps 1-6 for `instruction-multi-user.txt` → `instruction-multi-user.md.tmpl`.
8. `git rm instruction.txt instruction-multi-user.txt`.

## Todo List
- [x] Rewrite `instruction.txt` → `instruction.md.tmpl` with MD structure
- [x] Rewrite `instruction-multi-user.txt` → `instruction-multi-user.md.tmpl` with MD structure
- [x] Delete old `instruction.txt` and `instruction-multi-user.txt`
- [x] Diff-check: ensure no semantic content dropped (paragraph-by-paragraph read-through)

## Success Criteria
- Both `.md.tmpl` files exist, parse as valid Markdown.
- Old `.txt` files removed from working tree.
- Content diff (rendered text only, ignoring format chars): zero missing sentences vs. the old `.txt`.

## Risk Assessment
- **Risk**: accidental content drop during rewrite. **Mitigation**: do the rewrite section by section, each with an explicit before/after check.
- **Risk**: code blocks with long lines wrap awkwardly in PDF. **Mitigation**: phase 04 visual check; CSS `pre { overflow-wrap: break-word }` stub in phase 02.

## Security Considerations
- None. Content is public-facing instructions; no secrets.

## Next Steps
- Phase 02 consumes these templates to build the render pipeline.
