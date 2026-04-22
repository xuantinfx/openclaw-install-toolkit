---
type: brainstorm
date: 2026-04-22
slug: personalized-pdf-delivery
plan: ../260422-1232-personalized-pdf-delivery/plan.md
---

# Brainstorm — Personalized PDF Delivery

## Problem
- Today: delivery zip ships `instruction.txt` / `instruction-multi-user.txt` verbatim.
- Want: per-client personalized **PDF** with legal notice block at top naming the client, generated at build time.
- Header text (verbatim): "This AI setup document has been exclusively developed by **Brian Lab** for client **Jack Carter**. Any copying, use, or implementation without prior written authorization from Brian Lab is strictly prohibited and may result in legal liability under applicable copyright laws."

## Locked Decisions
| # | Decision | Rationale |
|---|---|---|
| 1 | Input = **interactive prompt** at build time, with `CLIENT_NAME` env override | Matches current build ergonomics; env-var escape hatch keeps CI/non-interactive working |
| 2 | Template fields = `{{client_name}}`, `{{delivery_date}}`, `{{build_id}}` | Lab name hardcoded ("Brian Lab") — one less thing to mistype |
| 3 | PDF style = **reformatted prose** (Markdown → PDF) | ASCII banners die; proper headings/lists. One-time rewrite cost, ongoing maint cheap |
| 4 | Delivery contents = **PDF only** (no txt alongside) | Single artifact per bundle; smaller legal-disclaimer blast radius |
| 5 | Zip naming = include **client slug** | `openclaw-toolkit-single-user-jack-carter.zip` — prevents cross-client mix-ups |
| 6 | Txt files in repo = **replaced** by `.md.tmpl` | Single source of truth. Kills drift |
| 7 | Build ID = `YYYY-MM-DD-<short-sha>[-dirty]` | Traceable to exact commit; `-dirty` flags untracked builds |
| 8 | Toolchain = **`md-to-pdf` (npm)** | Repo already Node-ish; CSS styling; Chromium handles Unicode (incl. Vietnamese diacritics); active project |

## Rejected Alternatives
- **pandoc + wkhtmltopdf** — wkhtmltopdf unmaintained since 2023, risk grows over time
- **pandoc + xelatex** — ~4 GB TeX install; overkill for a 5-page doc
- **CLI flags for client name** — less friendly than a prompt; env override covers scripted case
- **Keep `.txt` alongside `.md.tmpl`** — two sources of truth = drift

## Architecture
```
 npm run build-delivery
 │
 ├─ prompt "Client name?" (or read $CLIENT_NAME)
 ├─ compute build_id = YYYY-MM-DD-<short-sha>[-dirty]
 ├─ compute slug    = unicode-normalize + lowercase + kebab
 │
 ├─ render-pdf.mjs  instruction.md.tmpl            → instruction.pdf
 │                   instruction-multi-user.md.tmpl → instruction-multi-user.pdf
 │   (substitute vars, prepend legal-header.md.tmpl, pipe through md-to-pdf + pdf-style.css)
 │
 ├─ stage delivery/single-user/  (install.sh, install.command, README.md, skills/, instruction.pdf)
 ├─ stage delivery/multi-user/   (... + instruction-multi-user.pdf)
 │
 └─ zip  openclaw-toolkit-single-user-<slug>.zip
         openclaw-toolkit-multi-user-<slug>.zip
```

## Files
**New**
- `instruction.md.tmpl` — replaces `instruction.txt`
- `instruction-multi-user.md.tmpl` — replaces `instruction-multi-user.txt`
- `scripts/legal-header.md.tmpl` — notice block prepended to every PDF
- `scripts/pdf-style.css` — body/heading/callout styling
- `scripts/render-pdf.mjs` — Node renderer (tmpl → PDF)

**Modified**
- `scripts/build-delivery.sh` — prompt, build_id, slug, render calls, zip naming
- `package.json` — `md-to-pdf` devDep + `render-pdf` script

**Deleted**
- `instruction.txt`, `instruction-multi-user.txt`

## Risks
| Risk | Severity | Mitigation |
|---|---|---|
| Puppeteer devDep ~100 MB | Low | Dev box only; accepted |
| ASCII-banner → MD rewrite may lose formatting nuance | Medium | Manual PDF eyeball on first build; content preserved verbatim |
| Interactive prompt breaks CI | Medium | `CLIENT_NAME` env override |
| Dirty repo shipped accidentally | Medium | `-dirty` suffix in build_id = visible in every PDF |
| README.md bundled without per-client notice | Low | By design — README is bundle-wide; notice is client-specific. Revisit if ever needed |

## Success Criteria
- `npm run build-delivery` → prompt → two zips with client slug in filename.
- PDF opens with NOTICE header at top naming client + date + build_id.
- PDF body renders all instruction steps cleanly with proper headings.
- `CLIENT_NAME="Nguyễn Văn A" npm run build-delivery` → diacritics render in PDF body; filename slugs to `nguyen-van-a`.
- `--no-zip` path still works; dirty-repo builds tagged `-dirty` in PDF.

## Unresolved Questions
- Should `README.md` inside the zip also carry the NOTICE? (Default: no — flag later if client confusion arises.)
- Logo/branding on PDF cover? (Out of scope v1 — CSS stub allows adding later without pipeline change.)
- Do we archive generated PDFs somewhere (e.g. `delivery/archive/<client>/<date>/`) for post-hoc proof of what was shipped? (Out of scope v1.)
