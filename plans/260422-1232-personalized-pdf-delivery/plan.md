---
status: code-complete
created: 2026-04-22
completed: 2026-04-22
scope: personalized-pdf-delivery
blockedBy: []
blocks: []
brainstorm: ../reports/brainstorm-260422-1232-personalized-pdf-delivery.md
---

# Personalized PDF Delivery — Implementation Plan

Replace txt-based instruction delivery with per-client personalized PDF. At build time prompt for client name (env override allowed), stamp legal notice header + delivery date + git-anchored build id, render Markdown templates to PDF via `md-to-pdf`, and emit client-slug-named zip bundles.

## Context Links
- Brainstorm: `../reports/brainstorm-260422-1232-personalized-pdf-delivery.md`
- Current build script: `scripts/build-delivery.sh`
- Current instruction sources: `instruction.txt`, `instruction-multi-user.txt`
- Delivery bundles emitted to: `delivery/single-user/`, `delivery/multi-user/`
- `md-to-pdf` (Node): https://www.npmjs.com/package/md-to-pdf

## Key Locked Decisions
- **Single source of truth**: `instruction.md.tmpl` + `instruction-multi-user.md.tmpl` replace the `.txt` files. Old `.txt` files deleted in same phase to prevent drift.
- **Template vars**: exactly three — `{{client_name}}`, `{{delivery_date}}`, `{{build_id}}`. Lab name hardcoded ("Brian Lab") in legal header. Regex replace — no template engine.
- **Legal header lives in ONE file** (`scripts/legal-header.md.tmpl`) and is prepended to every rendered doc. Changing legal wording = edit one file.
- **Build ID**: `YYYY-MM-DD-<git short SHA>[-dirty]`. Dirty flag appended when `git status --porcelain` non-empty. Visible in PDF footer block.
- **Client input**: interactive prompt at build time. `CLIENT_NAME` env var overrides prompt (enables scripted/CI builds).
- **Slug**: Unicode-normalized (NFKD) → strip combining marks → lowercase → replace non-alphanumeric with `-` → collapse runs → trim. Handles `Nguyễn Văn A` → `nguyen-van-a`. PDF body preserves diacritics via Chromium.
- **Zip naming**: `openclaw-toolkit-<bundle>-<slug>.zip`. Empty slug guard: abort if slug is empty (indicates bad input, don't ship untagged zip).
- **PDF only** in zip — no `.txt` / `.md` artifact shipped. `README.md` stays generic (no per-client notice).
- **Toolchain**: `md-to-pdf` (npm devDep). Uses Puppeteer/Chromium — accepted ~100 MB dev install cost.

## Out of Scope
- Logo/cover-page branding. CSS stub present; add later without pipeline change.
- Multi-language instruction files. Template is English-only; client name may contain any Unicode.
- Archive of shipped PDFs. Zips are the ship artifact; no separate audit trail in v1.
- Injecting legal notice into `README.md` inside the zip (bundle-wide artifact, not client-specific).
- Signing / encrypting the PDF.

## Phases
| # | Name | File | Status |
|---|---|---|---|
| 01 | Rewrite instruction content as Markdown templates | `phase-01-rewrite-instruction-templates.md` | completed |
| 02 | Build render pipeline (node renderer + CSS + legal header) | `phase-02-build-render-pipeline.md` | completed |
| 03 | Wire render into build-delivery.sh | `phase-03-wire-build-delivery.md` | completed |
| 04 | End-to-end verification | `phase-04-e2e-verification.md` | completed |

## Dependencies
- Phase 02 depends on Phase 01 (renderer needs templates to exist).
- Phase 03 depends on Phase 02 (shell script calls the renderer).
- Phase 04 depends on Phase 03.

## Success Criteria
- `npm run build-delivery` → typing "Jack Carter" at prompt → produces:
  - `delivery/openclaw-toolkit-single-user-jack-carter.zip` containing `instruction.pdf`
  - `delivery/openclaw-toolkit-multi-user-jack-carter.zip` containing `instruction-multi-user.pdf`
- Both PDFs open with NOTICE header: "…developed by **Brian Lab** for client **Jack Carter**…" + delivery date + build_id line.
- `CLIENT_NAME="Nguyễn Văn A" npm run build-delivery` produces zips with slug `nguyen-van-a` and PDF body preserving diacritics.
- `scripts/build-delivery.sh --no-zip` still works; builds unzipped folders with personalized PDFs.
- Dirty-tree build → build_id ends with `-dirty` in PDF.
- No `.txt` file present anywhere in the delivery tree.

## Risk Summary
| Risk | Mitigation |
|---|---|
| ASCII-banner → MD rewrite loses visual hierarchy | Phase 04 manual PDF eyeball; headings mapped deliberately to `#`/`##` |
| Puppeteer install fails on dev box | Well-documented; known-good macOS arm64/x64. Fall-through mitigation: swap for pandoc+wkhtmltopdf if blocked |
| Interactive prompt breaks CI | `CLIENT_NAME` env override skips prompt |
| Empty/malformed client input → untagged zip | Slug empty-check aborts build |
| Legal text wording changes later | Centralized in `scripts/legal-header.md.tmpl` — single edit |

## Open Questions
- None blocking. Deferred decisions (README notice, logo, archive) listed in brainstorm.
