---
type: brainstorm
date: 2026-04-22
slug: instruction-rewrite
scope: instruction templates (single-user + multi-user), delivery bundle/PDF pipeline
decision: Interpretation A (doc-only, Terminal pairing preserved)
---

# Brainstorm — Instruction File Rewrite (5-key prep + images + templates)

## Problem

Current `instruction.md.tmpl` + `instruction-multi-user.md.tmpl`:
- Only 2 keys prepped upfront (Telegram bot token, Anthropic API key). 3 more keys (Firecrawl, Google AI, Brave) surface *mid-install* when `/content-monitor setup` runs — user stops, chases credentials, loses flow.
- Technical jargon sprinkled through steps (Gatekeeper, executable bit, port 18789).
- No visual aids; all-prose walkthrough.
- No copy-ready templates for terminal/bot input — users paraphrase, paste wrong things.
- No reference cheat-sheet of bot messages.

## Decisions (approved)

| # | Question | Answer |
|---|----------|--------|
| 1 | Scope | Both templates, mirrored |
| 2 | Key framing | All 5 required upfront |
| 3 | Image style | Relative `![alt](images/NN-foo.png)` tags |
| 4 | De-tech aggressiveness | Light — keep Way A/B + full troubleshooting |
| 5 | Pairing flow | **Interpretation A** — doc-only, Terminal `openclaw pairing approve telegram …` preserved (wrapped in template). Dashboard mentioned but off critical path. |

## Solution

### Top-level structure (both files, mirrored)

```
1.  Intro
2.  BEFORE YOU START — get these 5 keys ready
    2.1  Telegram bot token       (BotFather)
    2.2  Anthropic API key        (console.anthropic.com)
    2.3  Firecrawl API key        (firecrawl.dev)
    2.4  Google AI API key        (aistudio.google.com)
    2.5  Brave Search API key     (api.search.brave.com)
    2.X  ✅ Checklist table (numbered 1–5, tick before moving on)
3.  STEP 1 — Open Terminal                    [multi-user prepends "Log in"]
4.  STEP 2 — Unzip + run installer            (Way A / Way B; asks keys 1–2)
5.  STEP 3 — Open your OpenClaw dashboard     ← NEW (find tab opened by installer)
6.  STEP 4 — Say hi to your bot               (templated `hi` message block)
7.  STEP 5 — Approve yourself in Terminal     (templated `openclaw pairing approve …` block)
8.  STEP 6 — Set up the content monitor       (/content-monitor setup; asks keys 3–5)
9.  STEP 7 — Test (`manual test run`)
10. Troubleshooting
11. 📖 What you can say to your bot           ← NEW (reference cheat-sheet)
12. Keep these safe
```

### Per-key template (in Section 2)

```markdown
### 1 of 5 — Telegram bot token

**What it's for:** lets your computer talk to a Telegram bot.
**Where to get it:** [BotFather on Telegram](https://t.me/BotFather)
**What it looks like:** `1234567890:ABCdef...`

![Searching for BotFather](images/01-botfather-search.png)

1. Open Telegram, search `BotFather`, tap the one with a blue checkmark.
2. Send `/newbot`.
3. Pick a name, then a username ending in `bot`.
4. Copy the long code it sends back. Save it — you'll paste it later.

![BotFather reply with your token](images/02-botfather-token.png)
```

Same shape for keys 2–5. Each section carries: **What it's for**, **Where to get it** (clickable URL), **What it looks like** (prefix), 3–5 numbered steps, 2 image slots.

### Checklist table (end of Section 2)

```markdown
| # | Key                  | Looks like          | Got it? |
|---|----------------------|---------------------|---------|
| 1 | Telegram bot token   | `1234...:ABC...`    |   [ ]   |
| 2 | Anthropic API key    | `sk-ant-...`        |   [ ]   |
| 3 | Firecrawl API key    | `fc-...`            |   [ ]   |
| 4 | Google AI API key    | `AIzaSy...`         |   [ ]   |
| 5 | Brave Search API key | (long random)       |   [ ]   |
```

Numbering load-bearing — later steps say "paste key #1 when prompted" → zero chance of pasting Firecrawl into Anthropic prompt.

### Templated input blocks (every user-input moment)

**Telegram message:**
```markdown
📲 Copy this and send it to your bot:

    hi
```

**Terminal command with placeholder:**
```markdown
⌨️ Paste this into Terminal and press Enter
   (replace XXXXXXXX with the code from the bot's message):

    openclaw pairing approve telegram XXXXXXXX
```

Rule: no paragraph prose tells user what to type. Every input = labeled + fenced.

### Bot cheat-sheet (appendix)

```markdown
## 📖 What you can say to your bot

### Content monitor
| Say this                 | What happens                                     |
|--------------------------|--------------------------------------------------|
| `/content-monitor setup` | Starts guided setup (first-time).                |
| `setup content monitor`  | Same as above, plain-English version.            |
| `manual test run`        | Runs pipeline once so you can verify it works.   |
| `approve`                | Approves the most recent draft.                  |
| `what's new today?`      | Asks for today's topic suggestions.              |

### General
| Say this                 | What happens                                     |
|--------------------------|--------------------------------------------------|
| `hi`                     | Greets bot; first time, triggers pairing.        |
| Free-text question       | Regular AI assistant.                            |
```

### Image placeholders (~25 slots)

Folder: `images/` at repo root, next to `instruction.md.tmpl`. Naming: `NN-<what>.png`, zero-padded, reading order.

```
01-botfather-search           14-finder-zip
02-botfather-token            15-unzipped-folder
03-anthropic-signup           16-way-a-drag
04-anthropic-create-key       17-way-b-rightclick
05-anthropic-key-reveal       18-way-b-gatekeeper
06-firecrawl-dashboard        19-installer-running
07-firecrawl-create-key       20-installer-success
08-google-ai-studio           21-dashboard-opened
09-google-ai-create-key       22-telegram-bot-greeting
10-brave-dashboard            23-pairing-message
11-brave-generate-key         24-approval-success
12-terminal-spotlight         25-content-monitor-setup
13-terminal-open              26-test-run-result
```

User provides placeholder PNGs (even blank). Broken-image icons OK during dev — marks the slot.

### Pipeline changes

`scripts/render-pdf.mjs` already resolves relative paths from template dir — no change. `md-to-pdf` via Puppeteer embeds images into PDF. ✅

`scripts/build-delivery.sh` changes:
- Add `images` to the `required=(…)` array (fail-fast).
- `cp -R images "delivery/$single_dir/"` and `cp -R images "delivery/$multi_dir/"` — so unzipped-bundle readers also see images.
- No other changes. PDFs auto-embed images; zip ships markdown + images.

### De-tech rules (light touch)

- "executable mark" → "permission to run"
- "Gatekeeper" → omit word, describe pop-up
- `OPENCLAW_NO_DASHBOARD=1` → move to troubleshooting appendix
- Port 18789/90 (multi-user) → rewrite as "your install reserves a unique slot — the number after the colon is yours"
- Keep literal "unidentified developer" wording — matches the system pop-up

## Success criteria

- Non-technical user goes from zip → working bot in ≤20 min without leaving instruction.
- Zero "where do I get X?" moments mid-install.
- Every "get a key" section has: clickable link, visible prefix, 2 image slots, ≤5 numbered steps.
- Every user-typed input wrapped in copy-ready fenced block.
- Both `.tmpl` files identical in structure; diff = multi-user-specific layers only.
- PDF renders with images embedded; zip contains images folder.

## Trade-offs accepted

| Risk | Mitigation |
|------|------------|
| Brave is technically optional — marking required costs user ~2 min extra | Keeps narrative linear (user choice). |
| ~25 placeholder slots is a lot to produce | Guide works without them. Fill in progressively. |
| Two mirrored `.tmpl` files = double edit cost | Accept. Propose shared-fragment source only if maintenance pain emerges. |
| User pastes wrong key into wrong prompt | Numbered 1–5 checklist + numbered paste prompts mitigate. |

## Out of scope

- Any backend change to Telegram bot or pairing logic. (That would be Interpretation B — deferred.)
- Shared-fragment templating system to dedupe the two `.tmpl` files.
- Content-monitor `setup.sh` changes (prompt order already matches checklist).
- Re-generating actual screenshots — user owns that task.

## Next step

`/ck:plan` → implementation plan at `plans/260422-2034-instruction-rewrite/`.
