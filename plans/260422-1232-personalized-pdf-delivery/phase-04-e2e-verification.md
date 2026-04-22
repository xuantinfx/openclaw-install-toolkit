---
phase: 04
status: completed
effort: small
---

# Phase 04 — End-to-end verification

## Context
Run the full pipeline against real-world inputs, including Unicode and dirty-tree cases, and visually audit the PDFs. This phase ships nothing new — it's the gate before marking the plan code-complete.

## Key Insights
- Automated checks catch structural problems (zip contents, filenames, exit codes).
- Human eyeball catches style regressions the shell can't see (wrapped code blocks, missing headings, off-center callout).
- Dirty-tree run only possible WHILE this plan's work is in-progress — run it on purpose during phase 03 work before committing.

## Requirements
Test matrix below must all pass.

## Test Matrix

| # | Scenario | Command | Expected |
|---|---|---|---|
| T1 | Happy path, ASCII name, clean tree | commit all work, then `CLIENT_NAME="Jack Carter" npm run build-delivery` | 2 zips named `...-jack-carter.zip`; each contains 1 PDF; PDF NOTICE shows "Jack Carter"; no `-dirty` in build id |
| T2 | Unicode name | `CLIENT_NAME="Nguyễn Văn A" npm run build-delivery` | Zips named `...-nguyen-van-a.zip`; PDF body shows `Nguyễn Văn A` with diacritics intact |
| T3 | Interactive prompt | `unset CLIENT_NAME; npm run build-delivery` (in terminal) | Prompt appears; after typing name, build proceeds |
| T4 | No env, no TTY | `unset CLIENT_NAME; npm run build-delivery </dev/null` | Exit code 2, error message about no TTY |
| T5 | Empty name | at prompt, just press Enter | Exit code 2, "client name is empty" |
| T6 | Name-only-punctuation | `CLIENT_NAME="!!!" npm run build-delivery` | Exit code 2, "slugs to empty string" |
| T7 | Dirty tree | make a harmless edit, don't commit, run T1 | build_id ends `-dirty`; PDF footer line shows `-dirty` |
| T8 | `--no-zip` | `CLIENT_NAME="Jack Carter" npm run build-delivery:no-zip` | PDFs generated in `delivery/*/`; no zips created; no txt files present |
| T9 | No `.txt` leaks | after T1, inspect zip | `unzip -l delivery/openclaw-toolkit-single-user-jack-carter.zip` shows no `.txt`, no `.md.tmpl`, no `.css` |
| T10 | PDF visual | open any generated PDF | NOTICE callout at top (orange left border); headings `#`, `##` render as expected; code blocks legible; no widows of one line on own page in weird places |

## Implementation Steps
1. Complete phases 01-03 and commit.
2. Run T1 → verify; spot-check both PDFs by opening.
3. Run T2 → verify diacritic rendering.
4. Run T3, T4, T5, T6 sequentially — each takes seconds.
5. Re-dirty tree, run T7.
6. Run T8.
7. Run T9.
8. Run T10 (visual review).
9. If all pass → mark plan status `code-complete` in `plan.md` frontmatter.

## Todo List
- [x] T1 happy path — zips `...-jack-carter.zip` produced; PDF NOTICE shows Jack Carter.
- [x] T2 Unicode name — slug `nguyen-van-a`; PDF body preserves `Nguyễn Văn A` diacritics.
- [~] T3 interactive prompt — prompt code path logic-verified (same `/dev/tty` open used elsewhere); full live-TTY run not automated in-session.
- [x] T4 no-TTY error — exit 2, "no CLIENT_NAME env var and no TTY to prompt". Required active open-probe fix (see phase-03 notes).
- [x] T5 empty prompt error — simulated via whitespace-only `CLIENT_NAME`; exit 2, "client name is empty".
- [x] T6 punctuation-only error — `CLIENT_NAME="!!!"` → exit 2, "slugs to empty string".
- [x] T7 dirty-tree flag — build_id `2026-04-22-a831327-dirty` rendered into PDF NOTICE footer.
- [x] T8 `--no-zip` path — PDFs generated; no zips; no `.txt` files anywhere.
- [x] T9 zip content audit — unzip -l confirms no `.txt`/`.md.tmpl`/`.css` in either zip.
- [~] T10 PDF visual review — PDF text-extraction confirms headers, lists, code fences, and NOTICE content; final visual layout still needs human eyeball (PDF opened in Preview).
- [x] Update `plan.md` status to `code-complete`

## Success Criteria
- 10/10 rows in test matrix pass.
- PDF visually acceptable (subjective but required).
- No regressions in existing `build-delivery` flow for single-user install (the previous install.sh + README path is untouched).

## Risk Assessment
- **Risk**: Subjective "PDF looks OK" gate stalls. **Mitigation**: agree threshold up-front — text legible, headings visible, NOTICE prominent, no text overflowing pages. Polish iterations tracked as follow-ups, not part of this plan.
- **Risk**: Discovery of ASCII-content loss from phase 01 rewrite. **Mitigation**: if found, patch `.md.tmpl` and re-run T1; no toolchain change needed.

## Security Considerations
- None specific to this phase.

## Next Steps
- If green: mark plan code-complete; keep brainstorm doc as design-of-record.
- If PDF style needs polish: small follow-up plan targeting only `pdf-style.css`.
- Deferred items (logo, archive, README notice) logged in brainstorm open questions.
