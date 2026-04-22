# Content Monitor — Pipeline Workflow Docs

Full reference for how the content pipeline works, script by script.

---

## Overview

```
Competitor Sites (56)
       ↓ [weekly]
  crawl.py
       ↓
  sites/personal-injury/*.md
  sites/mortgage/*.md
       ↓ [daily 7AM]
  suggest_daily.py --record
       ↓
  content-calendar.json (2 new topics, 30-day dedup)
       ↓
  social_draft.py --from-calendar
       ↓
  posts/drafts/YYYY-MM-DD-HHMM/*.md (6 drafts)
       ↓ [user picks 1 or 2]
  generate_image.py --draft <path>
       ↓
  openclaw message send → Telegram (image preview)
       ↓ [user approves]
  approve_post.py --draft <path>
       ↓
  posts/approved/YYYY-MM-DD-HHMM/
       ↓ [user posts manually to Facebook + X]
  approve_post.py --publish <folder>
       ↓
  posts/published/YYYY-MM-DD-HHMM/
```

---

## Scripts Reference

### `suggest_daily.py`

Picks 2 unique content topics for today based on the weekly theme rotation. Records them to `content-calendar.json` to prevent repeats within 30 days.

```bash
# Standard daily run (records to calendar)
python3 suggest_daily.py --record

# View 30-day history
python3 suggest_daily.py --history

# Suggest without recording (dry-run)
python3 suggest_daily.py
```

**Output:** JSON array of 2 topic objects → also recorded in `content-calendar.json`

**Weekly theme map:**
| Day | Category | Theme |
|---|---|---|
| Monday | Personal Injury | know_your_rights |
| Tuesday | Mortgage/HEI | hei_education |
| Wednesday | Personal Injury | case_story |
| Thursday | Mortgage/HEI | market_news |
| Friday | Personal Injury | faq |
| Saturday | Mortgage/HEI | tips |
| Sunday | Both | industry_news |

---

### `social_draft.py`

Generates Facebook + X/Twitter posts for all topics recorded today in `content-calendar.json`. Outputs `.md` files in `posts/drafts/YYYY-MM-DD-HHMM/`.

```bash
# Generate drafts from today's calendar entries
python3 social_draft.py --from-calendar

# Generate draft for a custom topic
python3 social_draft.py --topic "What is shared equity?" --category mortgage --theme hei_education

# Generate with news context (run news_fetch.py first)
python3 social_draft.py --from-calendar --use-news
```

**Output format (each `.md` file):**
```
---
title: ...
category: personal-injury | mortgage | general
theme: ...
date: YYYY-MM-DD
status: draft
---

# Facebook Post
[full post, no links, max 400 words, 4-6 hashtags]

# X / Twitter Post
[≤280 chars, no links, 2-3 hashtags]

# Image Prompt (Gemini / AI image generator)
[detailed photorealistic prompt for generate_image.py]

# Review Checklist
- [ ] Review Facebook post
- [ ] Review X post
- [ ] Generate image
- [ ] Move to approved/
- [ ] Post manually
- [ ] Move to published/
```

**Post rules:**
- No links, no URLs — fully standalone
- Facebook: max 400 words, strong hook, 4-6 hashtags
- X: max 280 chars, punchy, 2-3 hashtags
- English only

---

### `news_fetch.py` *(optional)*

Fetches recent industry news via Brave Search to enrich drafts with real-world context.

```bash
# Requires BRAVE_API_KEY
BRAVE_API_KEY=<key> python3 news_fetch.py --theme know_your_rights
BRAVE_API_KEY=<key> python3 news_fetch.py --topic "home equity investment California 2025"
```

**Output:** Cached in `news/YYYY-MM-DD-<theme>.json`
Run this **before** `social_draft.py` if you want news-enriched posts.

---

### `generate_image.py`

Generates a 1080×1080px photorealistic image via Google Gemini (Nano Banana 2 → Imagen 4 → Imagen 4 Fast fallback chain).

```bash
# Generate for a specific draft (reads image prompt from the .md file)
GOOGLE_AI_API_KEY=<key> python3 generate_image.py --draft posts/drafts/2026-04-06-2226/my-post.md

# Generate with a custom prompt
GOOGLE_AI_API_KEY=<key> python3 generate_image.py \
  --prompt "Attorney reviewing case files, warm office lighting" \
  --slug my-post \
  --category personal-injury \
  --theme faq
```

**Model priority:**
| Model | Cost | Quality |
|---|---|---|
| Nano Banana 2 (Gemini 3.1 Flash Image) | ~$0.12/img | ⭐⭐⭐ Best |
| Imagen 4 | $0.03/img | ⭐⭐ Good |
| Imagen 4 Fast | $0.02/img | ⭐ Fallback |

**Image rules:**
- Always photorealistic — NEVER illustration, cartoon, icon, or symbol
- Wide or mid shots only — no close-up faces
- 1080×1080px (1:1 square) — optimal for Facebook + X
- No text/watermarks in image

**After generation:**
- Saved to `posts/images/<category>/<slug>-<date>.jpg`
- Copied into the draft folder alongside the `.md` file

**Send to Telegram immediately after generation:**
```bash
openclaw message send --channel telegram --target 1745276153 \
  --media posts/drafts/<folder>/<image>.jpg \
  --message "📸 [Post Title] — ready for review"
```

---

### `crawl.py`

Scrapes competitor sites using Firecrawl and saves markdown content to `sites/` folder. Respects crawl frequency per site to avoid hammering.

```bash
# Crawl all due sites (weekly schedule)
FIRECRAWL_API_KEY=<key> python3 crawl.py --schedule

# Force crawl all sites regardless of schedule
FIRECRAWL_API_KEY=<key> python3 crawl.py --schedule --force

# Crawl a single site
FIRECRAWL_API_KEY=<key> python3 crawl.py --url https://www.sweetjames.com
```

**Crawl frequency:**
- High-priority sites: weekly
- Standard sites: bi-weekly
- Tracks timestamps in `crawl-state.json`

**Firecrawl limits:**
- Free: 500 credits/month
- Paid: 3,000 credits/month ($16)
- 1 credit ≈ 1 page scraped

---

### `approve_post.py`

Moves a draft (+ image) into `posts/approved/` for posting, or into `posts/published/` after posting.

```bash
# Approve a draft (moves to posts/approved/YYYY-MM-DD-HHMM/)
python3 approve_post.py --draft posts/drafts/2026-04-06-2226/my-post.md

# Mark as published (moves from approved/ to published/)
python3 approve_post.py --publish posts/approved/2026-04-06-2232/
```

---

## Full Daily Sequence (Manual)

```bash
WORKSPACE=~/.openclaw/workspace
cd $WORKSPACE

# Step 1 — Pick today's topics
python3 skills/content-monitor/scripts/suggest_daily.py --record

# Step 2 (optional) — Enrich with news
BRAVE_API_KEY=<key> python3 skills/content-monitor/scripts/news_fetch.py --theme <today-theme>

# Step 3 — Generate drafts
python3 skills/content-monitor/scripts/social_draft.py --from-calendar

# Step 4 — Pick a draft, generate image
GOOGLE_AI_API_KEY=<key> python3 skills/content-monitor/scripts/generate_image.py \
  --draft posts/drafts/<folder>/<slug>.md

# Step 5 — Send image to Telegram
openclaw message send --channel telegram --target 1745276153 \
  --media posts/drafts/<folder>/<slug>-<date>.jpg \
  --message "📸 <Post Title>"

# Step 6 — Approve
python3 skills/content-monitor/scripts/approve_post.py \
  --draft posts/drafts/<folder>/<slug>.md

# Step 7 — After posting manually
python3 skills/content-monitor/scripts/approve_post.py \
  --publish posts/approved/<folder>/
```

---

## Cron Job (Automated Morning Briefing)

**Schedule:** 7:00 AM Asia/Saigon, every day
**Delivery:** Telegram → user ID `1745276153`

The cron runs steps 1–3 automatically in an isolated session, then sends a morning briefing text message. After user picks a post, the agent runs steps 4–5, then waits for approval.

To re-create the cron job on a new machine, tell the agent:
> "Setup content monitor cron job at 7AM Asia/Saigon, send results to my Telegram"

---

## Data Files

| File | Purpose | Auto-created? |
|---|---|---|
| `content-calendar.json` | 30-day topic history, prevents duplicates | ✅ |
| `crawl-state.json` | Last crawl timestamps per site | ✅ |
| `posts/drafts/` | Agent-generated drafts awaiting user review | ✅ |
| `posts/approved/` | Approved, ready to post manually | ✅ |
| `posts/published/` | Archived after posting | ✅ |
| `sites/personal-injury/` | Competitor scraped content | ✅ (after crawl) |
| `sites/mortgage/` | Competitor scraped content | ✅ (after crawl) |
| `news/` | Industry news cache by date + theme | ✅ (after news_fetch) |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `suggest_daily.py` gives no output | Check `content-calendar.json` is writable |
| All topics exhausted | Calendar auto-resets after 30 days; or delete `content-calendar.json` |
| `social_draft.py` no drafts generated | Make sure `suggest_daily.py --record` ran first today |
| Image generation fails | Verify `GOOGLE_AI_API_KEY` is set and billing enabled at aistudio.google.com |
| Telegram send fails | Check `openclaw status` — gateway must be running |
| Firecrawl rate limit | Reduce crawl frequency; use `--url` for single sites |
| News not in draft | Run `news_fetch.py` before `social_draft.py` |
| Duplicate topics appearing | Check `content-calendar.json` for corruption; re-run `--record` |
