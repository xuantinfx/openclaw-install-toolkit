---
status: code-complete
created: 2026-04-22
completed: 2026-04-22
scope: instruction-rewrite-5-keys-images
slug: instruction-rewrite
brainstorm: ../reports/brainstorm-260422-2034-instruction-rewrite.md
blockedBy: []
blocks: []
---

# Instruction File Rewrite — Implementation Plan

Rewrite `instruction.md.tmpl` + `instruction-multi-user.md.tmpl` to: centralize all 5 API keys upfront (Telegram, Anthropic, Firecrawl, Google AI, Brave), add placeholder image slots that embed into the delivered PDF, wrap every user-typed input (terminal + Telegram) in copy-ready templates, and append a bot-message cheat-sheet. Light de-tech; Way A/Way B install paths and full troubleshooting preserved. No installer or skill-code changes.

## Context Links

- Brainstorm: [../reports/brainstorm-260422-2034-instruction-rewrite.md](../reports/brainstorm-260422-2034-instruction-rewrite.md)
- Files in play:
  - `instruction.md.tmpl` (repo root)
  - `instruction-multi-user.md.tmpl` (repo root)
  - `scripts/build-delivery.sh` (add `images/` to required list + copy into bundles)
  - `scripts/render-pdf.mjs` — no change needed (resolves relative paths already)
  - NEW: `images/` folder at repo root (~26 placeholder PNGs)
- Prior related plan (completed): `../260422-1232-personalized-pdf-delivery/` — established PDF pipeline, provides substitution hooks (`{{zip_name}}`, etc.).

## Key Locked Decisions

- Interpretation A: Terminal-based pairing (`openclaw pairing approve telegram CODE`) stays — no bot/dashboard code change.
- All 5 keys marked required (Brave included) to keep narrative linear.
- Relative markdown images: `![alt](images/NN-foo.png)`. Images folder lives at repo root; copied into each delivery bundle; auto-embedded into PDF by `md-to-pdf` + Puppeteer.
- Both `.tmpl` files mirror each other. Multi-user = same structure + extra "log in" step + port-conflict troubleshooting. No shared-fragment system (YAGNI).
- Light de-tech: remove jargon words but keep Way A/B and full troubleshooting list.
- Placeholder images can be blank/empty PNGs for now — user supplies actual screenshots later. Broken-image icons OK during dev.

## Phases

| # | Phase | Status | Summary |
|---|-------|--------|---------|
| 01 | [Images scaffold + build pipeline](phase-01-images-and-build.md) | ✅ completed | 26 placeholder PNGs + README.md created; `build-delivery.sh` now requires + copies `images/`. Smoke-tested. |
| 02 | [Rewrite single-user instruction](phase-02-rewrite-single-user.md) | ✅ completed | `instruction.md.tmpl` rewritten: 7 STEPs, 5 key sub-sections, 26 image refs, 7 templated input blocks, bot cheat-sheet. 379 lines. |
| 03 | [Rewrite multi-user instruction](phase-03-rewrite-multi-user.md) | ✅ completed | `instruction-multi-user.md.tmpl` mirrored: 8 STEPs, Mac-login wrapper, port blurb, multi-user troubleshooting + "Keeping things tidy" preserved. 437 lines. |
| 04 | [Build + validate](phase-04-build-validate.md) | ✅ completed | Both PDFs rendered (8 pages each), both zips contain `images/` with 26 PNGs; all grep structural checks pass; image-ref cross-check clean. |

## Success Criteria

- `scripts/build-delivery.sh` succeeds with new `images/` required check.
- Both PDFs (`delivery/*.pdf`) render with image slots visible (placeholders or real).
- Both zip bundles contain `images/` folder sibling to `install.sh`.
- Both instruction docs render with: 5-key upfront section, numbered checklist, templated input blocks for every `hi` / `openclaw pairing …` / `/content-monitor setup` / `manual test run` prompt, and bot cheat-sheet at end.
- No regressions: all existing content preserved (install paths, troubleshooting, security note).

## Key Dependencies

- `md-to-pdf` (already in `package.json` from prior plan).
- `zip` CLI (already required by build script).
- Node.js (already required).
- No new runtime deps.

## Risks

| Risk | Mitigation |
|------|------------|
| Placeholder PNGs missing/corrupt → PDF build fails | Use minimal valid 1×1 PNGs; verify byte-level validity during Phase 01. |
| Image paths don't resolve during PDF render | `md-to-pdf` + Puppeteer use template file dir as baseURL; already validated by prior PDF plan. Smoke-test in Phase 04. |
| Two `.tmpl` files drift over time | Accept for now. Note in plan + add a comment at top of each file pointing to its sibling. |
| Content-monitor `setup.sh` prompt order changes later → cheat-sheet desync | Add a comment inline referencing the checklist order. |

## Out of Scope

- Bot/dashboard code changes (Interpretation B).
- Shared-fragment templating to dedupe the two `.tmpl` files.
- Real screenshots — user produces separately.
- Content-monitor skill edits.
