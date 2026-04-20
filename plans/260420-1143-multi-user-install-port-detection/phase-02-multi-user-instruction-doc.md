# Phase 02 — `instruction-multi-user.txt` Doc

## Overview

**Priority:** P1 (required UX — users won't know the multi-user story without it)
**Status:** pending
**Effort:** S (1 new plain-text file, ~80 lines; 1-line edit to existing doc)

Ship a short companion doc for the "2+ people sharing one Mac" scenario. Keep the main `instruction.txt` clean for the common single-user case.

## Context Links

- `instruction.txt` — existing single-user walk-through (216 lines, stable tone: plain language, no jargon, numbered steps)
- `plan.md` — this plan's decisions
- Phase 1 — script behaviour the doc describes

## Key Insights

- Existing `instruction.txt` reads at a ~10th-grade level ("black window for typing commands", "long code that looks like"). Match that voice — no developer jargon in the new doc either.
- Most of the flow is **identical** to the single-user doc. Only the port line and the "each person needs their own keys" bits are new. Cross-reference instead of duplicating.
- End users will never type `lsof` unprompted. Keep troubleshooting simple; if they're hitting "all ports busy", they need a developer's help anyway.

## Requirements

### Functional

- R1: Explains who the doc is for (multi-user Mac).
- R2: Lists what must NOT be shared between users (bot token, API key).
- R3: Points at `instruction.txt` for the common steps instead of duplicating them.
- R4: Surfaces the port line in installer output so users know where "their" gateway lives.
- R5: Minimal troubleshooting — stale daemons, port range exhausted.
- R6: `instruction.txt` gets a single line near the top pointing to the new doc.

### Non-functional

- Voice matches `instruction.txt` — plain, numbered, no jargon.
- Plain ASCII text, line length ≤ 80 chars (matches existing file).
- Under 100 lines.

## Related Code Files

- **Create:** `instruction-multi-user.txt` (repo root, next to `instruction.txt`)
- **Modify:** `instruction.txt` — insert one pointer line after the intro paragraph
- **No script changes in this phase.**

## Implementation Steps

### 1. Write `instruction-multi-user.txt`

Outline (final wording at author's discretion):

```
Sharing one Mac with someone else? Read this.
=============================================

Who this is for:
  Two or more people sharing the same Mac, where each person has their
  own macOS login (their own name in the top-right menu). If it's just
  you on the Mac, ignore this file — follow instruction.txt instead.

What you each need (cannot be shared):
  - Your own Telegram bot (each person runs BotFather and creates one).
  - Your own Anthropic API key (each person signs up at console.anthropic.com).
  - Your own copy of the toolkit zip, unzipped inside your own user folder.

Why separate bots and keys:
  Only one bot can be "connected" to a given OpenClaw install. If you
  and your housemate share one bot, your messages would all land on
  whichever Mac login happened to start first.

How to install (each person, one at a time):

  1. Log into your own macOS account.
  2. Follow instruction.txt from STEP 1 to STEP 7. Everything works the
     same as if you were the only person on the Mac.
  3. Watch for this line near the end of the installer:

         [OK] gateway healthy on 127.0.0.1:18790

     The number after the colon is YOUR port. The first person on the
     Mac usually gets 18789, the second person gets 18790, and so on.
     You don't need to do anything with this number — just know it's
     yours.

Can we install at the same time?
  You can, but it's cleaner if one person finishes first. The installer
  picks a free port by probing what's currently in use. If two installers
  probe at the exact same second, they might both land on the same port.
  Re-running the installer fixes it if that happens.

Troubleshooting:

  "no free port in 18789-18798"
    All ten reserved ports are taken. Usually this means old OpenClaw
    daemons are still running from past installs. Ask whoever set up
    the Mac, or run:
        lsof -iTCP:18789-18798 -sTCP:LISTEN
    to see what's holding them.

  Your bot replies with someone else's messages
    You're probably pointing at a bot that's already paired with
    another person's install. Make a new bot with BotFather and re-run
    the installer — you'll be asked for the new bot token.

  Bot stopped replying after the other person installed
    Check the port number in your install's success line is still the
    same as when you first installed. If it changed, your launchd
    service needs a kick:
        openclaw gateway restart
```

### 2. Insert pointer in `instruction.txt`

Add one line after the intro block (before "BEFORE YOU START"):

```
Sharing this Mac with someone else? After reading this file, also see
instruction-multi-user.txt for what changes when two people install.
```

Location: between line 13 ("The whole setup takes about 10-15 minutes.") and line 15 ("BEFORE YOU START — get these two things ready").

## Todo List

- [ ] Draft `instruction-multi-user.txt` matching tone of `instruction.txt`
- [ ] Insert pointer line in `instruction.txt`
- [ ] Read both files end-to-end as if you've never seen the project — does the story hang together?
- [ ] `wc -l instruction-multi-user.txt` — confirm under 100 lines
- [ ] Line length check — no lines over 80 chars

## Success Criteria

1. `instruction-multi-user.txt` exists, under 100 lines, matches the plain voice of `instruction.txt`.
2. `instruction.txt` has exactly one new pointer line; nothing else changed.
3. A fresh reader can follow the combined docs without seeing code snippets or jargon.
4. No markdown syntax in the `.txt` files — plain text only.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Doc drifts out of sync with script behaviour | Medium | Low | Script + doc ship in same PR; anchor troubleshooting on observable output, not implementation. |
| Voice mismatch with `instruction.txt` | Low | Low | Review side-by-side before commit. |

## Security Considerations

- Reminds users that bot tokens and API keys must NOT be shared across accounts.
- No change to on-disk permissions or secret-handling — the script enforces 0600 per-user.

## Next Steps

Commit Phase 1 + Phase 2 together — neither is useful alone.
Manual verification (from Phase 1 success criteria) doubles as validation for Phase 2's port-line claim.
