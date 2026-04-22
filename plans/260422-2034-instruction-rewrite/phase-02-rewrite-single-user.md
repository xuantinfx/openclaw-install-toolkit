---
phase: 02
title: Rewrite single-user instruction
status: pending
priority: high
effort: medium
depends_on: [phase-01]
---

# Phase 02 — Rewrite `instruction.md.tmpl`

## Overview

Full rewrite of `instruction.md.tmpl` following the approved design: 5-key upfront prep, numbered checklist, templated input blocks, dashboard step (off critical path), Terminal pairing preserved (Interpretation A), bot-message cheat-sheet at end. Preserve: Way A/Way B install paths, full troubleshooting, "keep these safe" security note, `{{zip_name}}` substitution.

## Requirements

- Every "get a key" section follows identical 5-bullet shape (What it's for / Where / What it looks like / Steps / 2 image slots).
- Numbered checklist table (keys 1–5) at end of Section 2.
- All user-typed inputs (terminal + Telegram) wrapped in labeled fenced blocks with placeholder conventions (⌨️ for terminal, 📲 for Telegram).
- Clickable markdown links on every key-provider URL.
- Bot cheat-sheet appendix.
- Mention `{{zip_name}}` exactly once (Step 2 intro) — already the current convention.

## Section-by-section content spec

### Section 1 — Intro (preserve tone)

```markdown
# How to set up your OpenClaw AI assistant on Telegram

Hi! This guide helps you set up your own AI helper that you can chat with
inside Telegram. No coding background needed — just follow each step in order.

You'll use:
- **Terminal** on your Mac (the black window for typing commands — comes built in).
- **Telegram** on whichever device you already use it on.

The whole setup takes about 15–20 minutes. Most of that is collecting 5 keys
in Section 2 — once you have those, the install itself is quick.
```

### Section 2 — BEFORE YOU START (the centralized 5-key prep)

Intro paragraph:
```markdown
## BEFORE YOU START — get these 5 keys ready

Each key is free to start (a credit card may be required for 2 of them, but
you'll only be charged a few cents for light use). Collect all 5 first, then
come back here. Don't start the installer until the checklist at the end of
this section is fully ticked.
```

Then the 5 sub-sections — each identical shape. Example (key 1, full); others follow same skeleton:

```markdown
### 1 of 5 — Telegram bot token

**What it's for:** lets your computer talk to a Telegram bot.
**Where to get it:** [BotFather on Telegram](https://t.me/BotFather)
**What it looks like:** `1234567890:ABCdef...` (a number, a colon, then letters)

![Searching for BotFather in Telegram](images/01-botfather-search.png)

1. Open Telegram, search `BotFather`, tap the one with the blue checkmark.
2. Send `/newbot`.
3. Pick a display name, then a username ending in `bot` (e.g. `myhelperbot`).
4. Copy the long code BotFather replies with. Save it somewhere safe.

![BotFather's reply with your bot token](images/02-botfather-token.png)
```

**Key 2 — Anthropic API key**
- URL: `[console.anthropic.com](https://console.anthropic.com)`
- Looks like: `sk-ant-...`
- Steps: sign up / log in → add payment method (few cents per use) → API Keys → Create Key → copy (can't see it again).
- Images: `03-anthropic-signup.png`, `04-anthropic-create-key.png`, `05-anthropic-key-reveal.png` (3 images OK here — reveal screen is important).

**Key 3 — Firecrawl API key**
- URL: `[firecrawl.dev](https://www.firecrawl.dev/)`
- Looks like: `fc-...`
- Steps: sign up → Dashboard → API Keys → Create API Key → copy. Free tier = 500 credits/month (enough).
- Images: `06-firecrawl-dashboard.png`, `07-firecrawl-create-key.png`.

**Key 4 — Google AI API key**
- URL: `[Google AI Studio](https://aistudio.google.com/)`
- Looks like: `AIzaSy...`
- Steps: sign in with Google → Get API Key → Create API Key (pick or create a project) → copy. Enable billing at `[Google Cloud Billing](https://console.cloud.google.com/billing)` (pennies per image).
- Images: `08-google-ai-studio.png`, `09-google-ai-create-key.png`.

**Key 5 — Brave Search API key**
- URL: `[Brave Search API](https://api.search.brave.com/)`
- Looks like: a long random string (no fixed prefix).
- Steps: sign up → Dashboard → API Keys → pick Free plan (2,000 queries/month, plenty) → Generate API Key → copy.
- Images: `10-brave-dashboard.png`, `11-brave-generate-key.png`.

**Checklist table (end of Section 2):**
```markdown
### ✅ Ready to install?

| # | Key                  | Looks like          | Got it? |
|---|----------------------|---------------------|---------|
| 1 | Telegram bot token   | `1234...:ABC...`    |   [ ]   |
| 2 | Anthropic API key    | `sk-ant-...`        |   [ ]   |
| 3 | Firecrawl API key    | `fc-...`            |   [ ]   |
| 4 | Google AI API key    | `AIzaSy...`         |   [ ]   |
| 5 | Brave Search API key | long random string  |   [ ]   |

If any row is empty, scroll back up and finish that one first.
The installer asks for keys **#1 and #2**; the bot asks for **#3, #4, #5** in step 6.
```

### Section 3 — STEP 1: Open Terminal

Preserve current wording. Add images:
```markdown
![Pressing Cmd+Space opens Spotlight](images/12-terminal-spotlight.png)
![Terminal window open](images/13-terminal-open.png)
```

### Section 4 — STEP 2: Unzip + run installer

Keep Way A + Way B as-is (user chose "light de-tech"). Replace "executable mark" with "permission to run". Add images:
- `14-finder-zip.png` (before unzipping)
- `15-unzipped-folder.png` (after unzip — showing the 3 expected files)
- `16-way-a-drag.png` (drag-to-Terminal)
- `17-way-b-rightclick.png` (right-click → Open)
- `18-way-b-gatekeeper.png` (the "unidentified developer" dialog)
- `19-installer-running.png` (mid-install)
- `20-installer-success.png` (success banner)

Key paste moment gets template block:
```markdown
When the installer stops and asks, paste these keys from your checklist:

- **Telegram bot token:** paste key **#1** → Enter.
- **Anthropic API key:** paste key **#2** → Enter.
```

Mention dashboard opens automatically at end:
```markdown
At the end, a browser tab opens automatically — that's your **OpenClaw
Control UI (dashboard)**. Don't close it; you'll use it in the next step.
```

Preserve `OPENCLAW_NO_DASHBOARD=1` mention but move to Troubleshooting.

### Section 5 — STEP 3: Open your OpenClaw dashboard (NEW)

```markdown
## STEP 3 — Find your OpenClaw dashboard

The installer opened a browser tab titled **"OpenClaw Control UI"**. Switch to
that tab now (it should still be open from Step 2). You don't need to do
anything in it yet — just leave it open so you can glance at it while you set
up the bot.

![OpenClaw dashboard opened in browser](images/21-dashboard-opened.png)

If the tab isn't there — you closed it, or the installer couldn't open it —
open Terminal and run:

    openclaw dashboard

That will reopen it.
```

### Section 6 — STEP 4: Say hi to your bot

```markdown
## STEP 4 — Say hi to your bot

Open Telegram. In the search bar, type the bot username you chose with
BotFather and tap it.

📲 **Copy this and send it to your bot:**

    hi

![Sending "hi" to your bot](images/22-telegram-bot-greeting.png)

The bot will reply with something like this:

![Bot's pairing-request reply](images/23-pairing-message.png)

```
OpenClaw: access not configured.
Your Telegram user id: 1048152213
Pairing code: 6P25BBXP

Ask the bot owner to approve with:
openclaw pairing approve telegram 6P25BBXP
```

Don't worry — this is expected. The bot is asking you to prove you're the
owner. Next step approves it.
```

### Section 7 — STEP 5: Approve yourself

```markdown
## STEP 5 — Approve yourself in Terminal

Go back to your Terminal window. Look at the bot's reply above — copy the
**pairing code** (the 8-character code on the "Pairing code:" line).

⌨️ **Paste this into Terminal and press Enter** (replace `XXXXXXXX` with your
actual code):

    openclaw pairing approve telegram XXXXXXXX

![Terminal showing successful approval](images/24-approval-success.png)

Terminal should print a success confirmation. Now send your bot any message —
e.g. "hello" — and it will reply like a real assistant. You're paired.
```

### Section 8 — STEP 6: Set up the content monitor

```markdown
## STEP 6 — Set up the content monitor

Back in Telegram:

📲 **Copy this and send it to your bot:**

    /content-monitor setup

![Bot starting content-monitor setup](images/25-content-monitor-setup.png)

The bot will walk you through setup by asking questions. When it asks for
API keys, paste these from your checklist:

- **Firecrawl API key:** paste key **#3**.
- **Google AI API key:** paste key **#4**.
- **Brave Search API key:** paste key **#5**.

(If you don't have key #5 yet, press Enter to skip — you can add it later.
But it's free and takes 2 minutes; strongly recommended.)

Answer the remaining questions (website domain, sample posts, etc.) as the
bot asks.
```

### Section 9 — STEP 7: Test

```markdown
## STEP 7 — Test that it works

📲 **Copy this and send it to your bot:**

    manual test run

![Bot reporting a successful test run](images/26-test-run-result.png)

You should see the monitor run and report back what it found. Done! 🎉
```

### Section 10 — Troubleshooting (preserve + add 2)

Keep all 7 existing items. Add:
- **"The browser tab with the dashboard didn't open"** → run `openclaw dashboard` in Terminal.
- **"Don't want the dashboard to auto-open on install"** → re-run with `OPENCLAW_NO_DASHBOARD=1 bash install.sh`.
- De-jargon: replace "executable mark" → "permission to run"; "Gatekeeper" → describe pop-up without naming.

### Section 11 — 📖 What you can say to your bot (NEW cheat-sheet)

```markdown
## 📖 What you can say to your bot

A quick reference of messages the bot understands. Send any of these in
Telegram like a normal chat message.

### General
| Say this              | What happens                                  |
|-----------------------|-----------------------------------------------|
| `hi`                  | Greets the bot. First time = pairing request. |
| any free-text message | Regular AI-assistant reply.                   |

### Content monitor
| Say this                 | What happens                                        |
|--------------------------|-----------------------------------------------------|
| `/content-monitor setup` | Starts guided first-time setup.                     |
| `setup content monitor`  | Plain-English version of the same command.          |
| `manual test run`        | Runs the pipeline once so you can verify it works.  |
| `approve`                | Approves the most recent draft the bot showed you.  |
| `what's new today?`      | Asks the monitor for today's topic suggestions.     |

Add more bot skills later? Come back and check this section.
```

### Section 12 — Keep these safe (preserve)

Mostly unchanged. Update to mention all 5 keys, not just 2:

```markdown
## Keep these safe

Your 5 keys (Telegram bot token, Anthropic, Firecrawl, Google AI, Brave)
are like passwords. Don't share them in screenshots, chats, emails, or code
repositories. If one leaks, regenerate it on the provider's dashboard.
```

## Related Code Files

**Modify (full rewrite):**
- `instruction.md.tmpl`

**Unchanged (reference only):**
- `skills/content-monitor/setup.sh` (confirms prompt order: Firecrawl → Google AI → Brave = checklist #3 → #4 → #5).
- `install.sh` (confirms prompt order: Telegram → Anthropic = checklist #1 → #2).

## Todo List

- [ ] Back up current `instruction.md.tmpl` content mentally (or via git — working dir is clean).
- [ ] Write new content per spec above, section by section.
- [ ] Verify `{{zip_name}}` substitution token appears in Step 2 intro.
- [ ] Verify all 20 image references resolve to files created in Phase 01 (01–20 used here; 21–26 mostly in this file too).
- [ ] Count image refs — should be ~24–26 depending on how many keys want 2 vs 3 images.
- [ ] Local render check: `bash scripts/build-delivery.sh --no-zip` with `CLIENT_NAME=smoke` → open the generated PDF, spot-check structure + image embedding.

## Success Criteria

- File ≤ ~450 lines (soft ceiling; expansion from current ~210 is expected given new sections + image refs).
- 1 × H1, 11 × H2 (intro + Section 2 header + Steps 1–7 + Troubleshoot + Cheat-sheet + Safe) + 5 × H3 (the 5 keys).
- Every `hi`, `openclaw pairing approve`, `/content-monitor setup`, `manual test run` appears inside a fenced block inside a labeled "⌨️"/"📲" paragraph — NO bare prose saying "type `hi`".
- Checklist table has 5 rows with correct `Looks like` prefixes.
- Links: BotFather, console.anthropic.com, firecrawl.dev, aistudio.google.com, api.search.brave.com are all markdown `[text](url)` form.
- PDF (from smoke build) renders without errors; images appear (even as tiny dots).

## Risks

| Risk | Mitigation |
|------|------------|
| Over-expansion makes guide feel long | 450-line ceiling. Cut any section that doesn't add user value. |
| Image-path typos → broken refs | After writing, `grep -oE 'images/[a-z0-9-]+\.png' instruction.md.tmpl \| sort -u` → diff against `ls images/`. |
| `{{zip_name}}` token dropped accidentally | grep check in todo list. |

## Next Steps

Phase 03 mirrors this into `instruction-multi-user.md.tmpl` with Mac-login + port layers.
