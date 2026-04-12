---
name: content-monitor
description: >
  Monitor competitor websites (personal injury law CA/NV + mortgage/HEI), suggest unique daily
  content topics, generate standalone Facebook and X/Twitter posts (no links), and generate
  photorealistic images via Google Gemini API (Nano Banana 2 / Imagen 4). Prevents content
  duplication with 30-day rolling calendar. IMPORTANT: On first use or when user asks to set up,
  you MUST read prompts/setup-wizard.md and follow ALL steps in order — do NOT improvise your
  own setup flow. The wizard covers: websites, social media login via browser, sample posts,
  weekly themes, API keys, domain, and cron schedule (via CronCreate tool, NOT LaunchAgent).
  Trigger phrases: "suggest today's content", "generate social post", "crawl sites",
  "content calendar", "what should I post today", "morning briefing", "run content pipeline",
  "generate image", "setup content monitor", "configure content pipeline", "set up posting".
---

# Content Monitor Skill

Full content pipeline: crawl 56 competitor sites → suggest unique daily topics → generate Facebook + X posts (no links) → generate photorealistic image via Google Gemini → morning briefing for human review.

## Scope

- **Facebook post** — standalone, no links, value-first content
- **X/Twitter post** — standalone, no links, ≤280 chars
- **Photorealistic image** — generated via Google Nano Banana 2 / Imagen 4 (never illustrations/symbols)
- **No blog, no URLs in posts**

## API Keys Required

| Key | Purpose | Required? |
|---|---|---|
| `FIRECRAWL_API_KEY` | Crawl competitor sites | ✅ Yes |
| `GOOGLE_AI_API_KEY` | Generate images (Nano Banana 2 / Imagen 4) | ✅ Yes |
| `BRAVE_API_KEY` | Industry news enrichment | Optional |

## Prerequisites

- Python 3.9+
- Scripts: `skills/content-monitor/scripts/`
- Site list: `skills/content-monitor/references/sites.md`
- Content themes: `skills/content-monitor/references/themes.md`

## First-Time Setup

**CRITICAL**: On first use, or when the user says "setup content monitor" / "configure content pipeline" / "set up posting":

1. **READ `prompts/setup-wizard.md` FIRST** — this file contains the exact step-by-step setup flow
2. **Follow ALL steps in order** — do NOT skip steps or improvise your own setup flow
3. **Do NOT use LaunchAgent, crontab, or other OS-level scheduling** — use the CronCreate tool only
4. **Do NOT finish setup without completing ALL steps**:
   - Step 1: Welcome
   - Step 2: Competitor websites
   - Step 3: Social media login (Facebook + X via Playwright browser)
   - Step 4: Sample posts / writing style
   - Step 5: Weekly content themes
   - Step 6: **API keys** (Firecrawl, Google AI, Brave) — saved to `~/.openclaw/workspace/.env-content-monitor`
   - Step 7: Website domain
   - Step 8: **Cron schedule** via CronCreate tool
   - Step 9: Initialize workspace
   - Step 10: Show summary

**The setup wizard prompt is the source of truth. Read it. Follow it. Do not improvise.**

See also:
- [QUICKSTART.md](QUICKSTART.md) — Quick start guide
- [TOKEN-SETUP.md](TOKEN-SETUP.md) — How to get API keys (Gemini, Firecrawl, Brave)

## Workspace Structure

```
workspace/
├── sites/
│   ├── personal-injury/
│   │   ├── *.md              ← competitor content (raw markdown)
│   │   └── .topics/*.json    ← extracted topics per domain (auto by crawl.py)
│   └── mortgage/
│       ├── *.md
│       └── .topics/*.json
├── news/                     ← industry news cache by date+theme (.json + .md)
├── posts/
│   ├── drafts/               ← awaiting review
│   ├── images/               ← Google Gemini generated images
│   ├── approved/             ← reviewed, ready to post (+ AUTO-POST-INSTRUCTIONS.md)
│   └── published/            ← posted
├── content-calendar.json     ← 30-day topic history (no duplicates)
├── crawl-state.json          ← last crawl timestamps per site
└── skills/content-monitor/scripts/
    ├── crawl.py              ← Firecrawl scraper + topic extraction
    ├── news_fetch.py         ← Brave Search news (auto mode for daily pipeline)
    ├── suggest_daily.py      ← dynamic topic generation from news + competitor data
    ├── social_draft.py       ← Facebook + X drafts, varied structure, human tone
    ├── generate_image.py     ← Google Gemini image generator
    ├── approve_post.py       ← approve + optional auto-post trigger
    └── auto_post.py          ← generate browser posting instructions (CDP relay)
skills/content-monitor/prompts/
    └── setup-wizard.md       ← agent-driven first-time setup (conversational)
skills/content-monitor/references/
    ├── sites.md              ← monitored competitor sites
    ├── themes.md             ← weekly theme rotation + style guidelines
    ├── sample-posts.md       ← user-provided sample posts (from wizard)
    └── writing-style.md      ← AI-generated writing style guide (from samples)
```

## Daily Workflow

### Automated (7:00 AM Asia/Saigon via cron)
1. `news_fetch.py --auto` — fetch today's trending news (Brave Search)
2. `suggest_daily.py --record` — generate 3-5 topic candidates from news + competitor data
3. `social_draft.py --from-calendar` — generate Facebook + X drafts
4. **Send briefing** (text only — no image yet): show candidates with source type (news/competitor/evergreen)
5. **Wait for user to pick** which post(s) to use

### After user picks a post
1. `generate_image.py --draft <path>` — generate image for selected post only
2. **Send image to Telegram** via `openclaw message send --channel telegram --target 1745276153 --media <image_path> --message "<caption>"`
3. Show full post text (Facebook + X) to user for approval
4. On approval: `approve_post.py --draft <path> --auto-post` — moves to approved/ AND generates browser instructions
5. Agent reads `AUTO-POST-INSTRUCTIONS.md` and executes via browser CDP relay:
   - Opens Facebook → fills post + uploads image → clicks Post
   - Opens X → fills post + uploads image → clicks Post
6. After both posts published: `approve_post.py --publish <folder>` — moves to `posts/published/`

### Auto-post via browser relay
```bash
# Approve + generate posting instructions (agent executes via CDP)
python3 approve_post.py --draft <path> --auto-post

# Preview only (fill content but don't click publish)
python3 approve_post.py --draft <path> --auto-post --dry-run

# Generate instructions for a specific platform
python3 auto_post.py --draft <path> --facebook-only
python3 auto_post.py --draft <path> --x-only
```

**Requires**: OpenClaw Chrome browser relay active, Facebook + X logged in within the OpenClaw Chrome profile.

### Manual run
```bash
python3 skills/content-monitor/scripts/news_fetch.py --auto
python3 skills/content-monitor/scripts/suggest_daily.py --record
python3 skills/content-monitor/scripts/social_draft.py --from-calendar
GOOGLE_AI_API_KEY=<key> python3 skills/content-monitor/scripts/generate_image.py --draft posts/drafts/<category>/<slug>-<date>.md
```

### Manual run
```bash
python3 skills/content-monitor/scripts/news_fetch.py --auto
python3 skills/content-monitor/scripts/suggest_daily.py --record
python3 skills/content-monitor/scripts/social_draft.py --from-calendar
```

### Crawl competitor sites (weekly)
```bash
FIRECRAWL_API_KEY=<key> python3 skills/content-monitor/scripts/crawl.py --schedule
# First-time full crawl:
FIRECRAWL_API_KEY=<key> python3 skills/content-monitor/scripts/crawl.py --schedule --force
```

## Morning Briefing Format

```
Good morning! Here are today's [DATE] content candidates:

Post 1 — [CATEGORY] | [THEME] | Source: [news/competitor/evergreen]
Title: [TITLE]
[Facebook post preview — first 200 chars]
---
X: [X post]

Post 2 — [CATEGORY] | [THEME] | Source: [news/competitor/evergreen]
Title: [TITLE]
[Facebook post preview — first 200 chars]
---
X: [X post]

Post 3 — ...

Which post do you want to use today? I will generate the image after you choose.
Reply with the number, or "approve [number]" to auto-post directly.
```

## When User Picks a Post (After Morning Briefing)

1. Generate image: `generate_image.py --draft <path>`
2. **Send image directly to Telegram:**
   ```bash
   openclaw message send --channel telegram --target 1745276153 \
     --media <image_path> \
     --message "📸 [Post Title] — ready for review"
   ```
3. Then send the full post text (Facebook + X) as a separate message
4. On user saying "approve": `approve_post.py --draft <path>` moves both draft + image to `posts/approved/YYYY-MM-DD-HHMM/`
5. After user posts manually: `approve_post.py --publish posts/approved/YYYY-MM-DD-HHMM/`

## Post Guidelines

**Facebook:**
- No links, no URLs anywhere
- Max 400 words
- Human tone — write like a knowledgeable professional, not a marketing bot
- Varied structure (story, stat, question, myth, news angle, direct — rotated automatically)
- Max 1 emoji (at the start, optional) — NO emoji as bullet points
- End with max 3 hashtags on the last line
- No checkmark bullets, no generic CTAs

**X/Twitter:**
- No links, no URLs
- Max 280 characters
- Punchy, direct, one strong idea
- Max 2 hashtags
- No emoji

**Images (Google Gemini):**
- Always photorealistic — NEVER illustration, cartoon, symbol, icon
- Output: 1080×1080px (1:1) — optimal for Facebook + X
- Primary: Nano Banana 2 (~$0.12/img, best quality)
- Fallback: Imagen 4 ($0.03/img) → Imagen 4 Fast ($0.02/img)

| Theme | Visual |
|---|---|
| FAQ | Attorney consulting client, warm office |
| Know Your Rights | Confident attorney, law office |
| Case Story | Cinematic — accident scene or courthouse |
| HEI Education | Happy homeowner couple, suburban home |
| Market News | Real estate, neighborhood aerial |
| Tips | Financial advisor + homeowner |
| Industry News | Boardroom meeting, professionals |

## Weekly Theme Rotation

| Day | Category | Theme |
|---|---|---|
| Monday | Personal Injury | know_your_rights |
| Tuesday | Mortgage/HEI | hei_education |
| Wednesday | Personal Injury | case_story |
| Thursday | Mortgage/HEI | market_news |
| Friday | Personal Injury | faq |
| Saturday | Mortgage/HEI | tips |
| Sunday | Both | industry_news |

## Ad-hoc Commands

```bash
# View 30-day content history
python3 suggest_daily.py --history

# Generate draft for a custom topic
python3 social_draft.py --topic "What is shared equity?" --category mortgage --theme hei_education

# Generate image for a specific draft
GOOGLE_AI_API_KEY=<key> python3 generate_image.py --draft posts/drafts/personal-injury/slug-date.md

# Custom image prompt
GOOGLE_AI_API_KEY=<key> python3 generate_image.py --prompt "Attorney reviewing case files" --slug my-post --category personal-injury --theme faq

# Crawl single site
FIRECRAWL_API_KEY=<key> python3 crawl.py --url https://www.sweetjames.com

# Fetch industry news
BRAVE_API_KEY=<key> python3 news_fetch.py --topic "home equity investment California 2025"
```

## Key Rules

- **No links/URLs in posts** — Facebook and X are fully standalone
- **No image scraping** — all images generated by Google Gemini (copyright safe)
- **No duplicate topics** within 30 days — enforced by content-calendar.json
- **Drafts only** — human approves before any post goes live
- **English only** for all content
- **Always photorealistic images** — wide/mid shots only, no close-up faces
- **Human tone** — no emoji bullets, max 3 hashtags, varied post structures
- **News first** — `news_fetch.py --auto` runs before topic suggestion every day
- **Auto-post via browser relay** — after approval, agent posts to Facebook + X via CDP
- Firecrawl: free=500 credits/month, paid=3K/month ($16)
- Google AI: billing required — Nano Banana 2 ~$0.12/img, Imagen 4 $0.03/img

## Troubleshooting

| Issue | Fix |
|---|---|
| No suggestions today | Run `news_fetch.py --auto` then `suggest_daily.py --record` |
| Topics too generic | Check `sites/{category}/.topics/` — run `crawl.py --schedule` if empty |
| All topics used | Auto-resets after 30 days; add more competitor sites to expand pool |
| Image generation fails | Check `GOOGLE_AI_API_KEY` and billing at aistudio.google.com |
| `content-calendar.json` missing | Created automatically on first `--record` run |
| Firecrawl rate limit | Use `--url` for single sites; avoid daily `--force` |
| News not in draft | Ensure `news_fetch.py --auto` runs before `social_draft.py` |
| Auto-post fails | Check Chrome relay is active + logged in to Facebook/X |
| X image upload fails (element ref changes) | Use `evaluate` workaround: run `openclaw browser evaluate 'document.querySelector("input[data-testid=\"fileInput\"]").click()'` then immediately `openclaw browser upload <file>` — do NOT click the camera icon first |
| Posts still have emoji spam | Check `references/themes.md` for updated style guidelines |
