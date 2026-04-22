---
phase: 03
title: Rewrite multi-user instruction
status: pending
priority: high
effort: medium
depends_on: [phase-02]
---

# Phase 03 — Rewrite `instruction-multi-user.md.tmpl`

## Overview

Apply Phase 02's rewrite to the multi-user template, layering in shared-Mac specifics (per-user macOS login, per-user keys, port-conflict troubleshooting). Same image refs; most sections are copy-then-edit from the single-user rewrite.

## Requirements

- Same overall structure as single-user (Sections 1–12 identical numbering-wise).
- Multi-user specifics layered on top as inline paragraphs or extra step, not a separate structure.
- Zero divergence in the "get a key" sections other than wording like "use YOUR OWN account, not shared".
- Preserve: port-conflict troubleshooting, "Can we install at the same time?" FAQ, "Keeping things tidy" section.

## Section deltas vs single-user

| Section | Change relative to single-user |
|---------|-------------------------------|
| Title | "…on Telegram (shared Mac)" |
| Intro | Add: "This is the shared-Mac version. 'Shared Mac' means two or more people each have their OWN macOS login. If you're the only person who uses this Mac, use the single-user guide instead." |
| "WHAT YOU EACH NEED (CANNOT BE SHARED)" | Preserve existing sub-section — keep as intro paragraph above Section 2. Restate: every person needs own bot + own keys + own zip inside their own user folder. |
| Section 2 (5 keys) | Same key sub-sections. Add one sentence to keys 1 + 2: "use a bot name only YOU will use", "use your OWN Anthropic account (billing is per-account)". |
| Checklist | Identical table. Add one line above: "These 5 keys are PER PERSON. Your housemate will generate their own 5 when it's their turn." |
| Renumber steps: | STEP 1 now = "Log into YOUR OWN macOS account"; Terminal becomes STEP 2. Everything shifts by 1. |
| STEP 1 (new) — Log in | Preserve current wording: "Look at the top-right menu bar…" + short paragraph about `~/.openclaw` being per-user. |
| STEP 2 — Open Terminal | Same as single-user STEP 1. |
| STEP 3 — Unzip + run installer | Identical to single-user STEP 2, plus preserve the port-selection blurb: "Watch for `[OK] gateway healthy on 127.0.0.1:18790` — the number after the colon is YOUR slot. The installer picks a free one automatically." Move technical detail to troubleshooting. |
| STEP 4 — Open dashboard | Same content as single-user STEP 3. Note: each user sees their own dashboard on their own port, automatic. |
| STEP 5 — Say hi to bot | Same as single-user STEP 4. Add: "Make sure it's YOUR bot (the one YOU made with BotFather), not your housemate's." |
| STEP 6 — Approve yourself | Same as single-user STEP 5. Add: "Run this in Terminal **while logged in as you** — it writes to YOUR user folder." |
| STEP 7 — Content monitor setup | Same as single-user STEP 6. |
| STEP 8 — Test | Same as single-user STEP 7. Add closing: "If your housemate hasn't installed yet, they can now log out, let you log out, log in as themselves, and repeat from STEP 1." |
| "Can we install at the same time?" | Preserve current FAQ section. Goes between STEP 8 and Troubleshooting. |
| Troubleshooting | Preserve all current multi-user-specific items: `no free port in 18789-18798`, "bot replies with someone else's messages", "bot stopped replying after other person installed". Plus same 2 dashboard items added in Phase 02. |
| Cheat-sheet | Identical to single-user. |
| Keep these safe | Add: "Don't share your 5 keys with the other person on this Mac — they have their own. Your data lives in your own user folder (`~/.openclaw`)." |
| "KEEPING THINGS TIDY" | Preserve existing section as-is; rename to lowercase "Keeping things tidy". |

## Implementation Steps

1. Copy the fully-written `instruction.md.tmpl` (Phase 02 output) to `instruction-multi-user.md.tmpl` as a starting base.
2. Apply the deltas from the table above, section by section.
3. Renumber STEPs 1→2, 2→3, …, 7→8 (use a careful find/replace).
4. Preserve all current multi-user-specific blocks: "WHAT YOU EACH NEED", port blurb in installer step, "Can we install at the same time?", multi-user troubleshooting items, "KEEPING THINGS TIDY".
5. Verify image refs — same 26 images shared with single-user. No new images needed for multi-user.
6. Smoke render: `bash scripts/build-delivery.sh --no-zip` (`CLIENT_NAME=smoke`) → inspect `delivery/openclaw-toolkit-multi-user-smoke.pdf`.

## Related Code Files

**Modify (full rewrite):**
- `instruction-multi-user.md.tmpl`

## Todo List

- [ ] Start from Phase 02's single-user output as base.
- [ ] Apply Mac-login STEP 1; renumber all downstream STEPs.
- [ ] Add "WHAT YOU EACH NEED" block above Section 2.
- [ ] Add per-user phrasing to keys 1 + 2 in Section 2.
- [ ] Preserve port-selection blurb in installer step.
- [ ] Preserve "Can we install at the same time?" FAQ.
- [ ] Preserve multi-user troubleshooting items.
- [ ] Preserve "Keeping things tidy".
- [ ] Grep check: no "STEP 1 — Open Terminal" remains (should be STEP 2 here).
- [ ] Grep check: image refs all resolve (`images/NN-...png`).
- [ ] Smoke render → inspect multi-user PDF.

## Success Criteria

- Structure mirrors single-user exactly (same 12 sections, same headings, same cheat-sheet).
- Step count = 8 (vs 7 in single-user).
- All multi-user-specific content from current file preserved, just rewritten to match new tone.
- PDF smoke-render succeeds.
- Line count within ~50 lines of single-user file (modest expansion from shared-Mac layers is expected).

## Risks

| Risk | Mitigation |
|------|------------|
| Renumbering STEPs introduces off-by-one references (e.g. "see Step 4" pointing at wrong step) | After renumber, grep `grep -n "STEP [0-9]" instruction-multi-user.md.tmpl` → eyeball every cross-reference. |
| Divergence from single-user drifts over time | Add a comment at top of both files pointing to each other: `<!-- Mirrors instruction-multi-user.md.tmpl / instruction.md.tmpl — keep structure in sync -->`. |
| Multi-user blocks dropped during copy-edit | Pre-list them in Todo; tick each off. |

## Next Steps

Phase 04 builds both bundles, validates PDFs, zips.
