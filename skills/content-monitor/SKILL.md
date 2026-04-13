---
name: content-monitor
description: >
  Monitor competitor websites, suggest daily content, generate Facebook + X posts with images.
  TWO MANDATORY FLOWS — agent must follow exactly:
  (1) SETUP: On first use or "setup content monitor" → read AND follow prompts/setup-wizard.md 
  (2) POSTING: On "run content pipeline" or daily cron → read AND follow prompts/posting-flow.md
  Never improvise. Never go silent. Never use LaunchAgent. Always confirm each step with user.
  Trigger: "setup content monitor", "run content pipeline", "what should I post today",
  "morning briefing", "suggest today's content", "crawl sites", "content calendar".
---

# Content Monitor Skill

## ⚠️ AGENT: READ THIS FIRST

**Before doing ANYTHING, determine which flow applies:**

### Flow A: First-Time Setup
**Trigger**: first use, "setup content monitor", "configure content pipeline", "set up posting", or `~/.openclaw/workspace/.env-content-monitor` does not exist.

**Action**: READ the file `prompts/setup-wizard.md` and follow it step by step.

Quick reference (but you MUST read the prompt file for full instructions):

```
Step 1/7: Welcome → list 7 steps → WAIT for user to say "ready"
Step 2/7: Competitor websites → ask URLs or "use defaults" → confirm → WAIT
Step 3/7: Social media login → open Facebook in browser → WAIT for login → open X → WAIT → confirm → WAIT
Step 4/7: Writing style → ask for sample posts or skip → confirm → WAIT
Step 5/7: Weekly themes → show schedule → ask customize or keep defaults → confirm → WAIT
Step 6/7: API keys → ask Firecrawl key → WAIT → ask Google AI key → WAIT → ask Brave key → WAIT → save → confirm → WAIT
Step 7/7: Domain + Cron → ask domain → ask time → use CronCreate tool (NOT LaunchAgent) → confirm
Final: Init workspace → show summary → ask "want to run pipeline now?"
```

**Rules**: After EVERY step → confirm what was done → ask "Continue?" → WAIT for user.

### Flow B: Daily Posting
**Trigger**: "run content pipeline", "what should I post today", "morning briefing", daily cron.

**Action**: READ the file `prompts/posting-flow.md` and follow it step by step.

Quick reference (but you MUST read the prompt file for full instructions):

```
Step 1: Run pipeline scripts → show briefing with candidates → WAIT for user to pick
Step 2: Generate image → show post text + image → WAIT for user approval
Step 3: User says "approve" → proceed | "edit X" → edit and re-show | "skip" → cancel
Step 4: Approve post + prepare auto-post instructions
Step 5: Post to Facebook via browser → confirm success/failure → WAIT if failed
Step 6: Post to X via browser → confirm success/failure → WAIT if failed
Step 7: Archive to published/ → show final summary → suggest what's next
```

**Rules**: After EVERY step → confirm what was done → guide to next step → NEVER go silent.

### Flow C: Ad-hoc Commands
For other requests (crawl sites, content calendar, etc.) — see sections below.

---

## Scope

- **Facebook post** — standalone, no links, value-first content, max 400 words
- **X/Twitter post** — standalone, no links, ≤280 chars
- **Photorealistic image** — generated via Google Nano Banana 2 / Imagen 4
- **No blog, no URLs in posts**

## API Keys Required

| Key | Purpose | Required? |
|---|---|---|
| `FIRECRAWL_API_KEY` | Crawl competitor sites | Yes |
| `GOOGLE_AI_API_KEY` | Generate images (Nano Banana 2 / Imagen 4) | Yes |
| `BRAVE_API_KEY` | Industry news enrichment | Optional |

Stored in: `~/.openclaw/workspace/.env-content-monitor`

## Workspace Structure

```
~/.openclaw/workspace/
├── sites/{personal-injury,mortgage}/    ← scraped competitor content + .topics/
├── news/                                ← industry news cache
├── posts/
│   ├── drafts/                          ← awaiting review
│   ├── images/                          ← generated images
│   ├── approved/                        ← reviewed, ready to post
│   └── published/                       ← archive
├── content-calendar.json                ← 30-day topic tracker
├── crawl-state.json                     ← crawl timestamps
└── .env-content-monitor                 ← API keys (chmod 600)

skills/content-monitor/
├── prompts/
│   ├── setup-wizard.md                  ← MANDATORY: setup flow
│   └── posting-flow.md                 ← MANDATORY: posting flow
├── scripts/
│   ├── crawl.py                         ← Firecrawl scraper
│   ├── news_fetch.py                    ← Brave Search news
│   ├── suggest_daily.py                 ← topic generation
│   ├── social_draft.py                  ← content brief builder
│   ├── generate_image.py                ← Google Gemini image gen
│   ├── approve_post.py                  ← approve + auto-post
│   ├── auto_post.py                     ← browser posting instructions
│   └── setup_wizard.py                  ← utility CLI (used by agent)
└── references/
    ├── sites.md                         ← monitored sites
    ├── themes.md                        ← theme rotation + style
    ├── theme-schedule.json              ← custom weekly schedule
    ├── sample-posts.md                  ← user sample posts
    └── writing-style.md                 ← AI-generated style guide
```

## Post Guidelines

**Facebook:**
- No links, no URLs anywhere
- Max 400 words, human tone
- Varied structure (story, stat, question, myth, news angle, direct)
- Max 1 emoji (at start, optional), NO emoji as bullets
- Max 3 hashtags on last line

**X/Twitter:**
- No links, no URLs, max 280 characters
- Punchy, direct, one strong idea
- Max 2 hashtags, no emoji

**Images (Google Gemini):**
- Always photorealistic (NEVER illustration/cartoon)
- 1080×1080px, wide/mid shots only
- Primary: Nano Banana 2 (~$0.12/img) → Fallback: Imagen 4 ($0.03/img)

## Weekly Theme Rotation

Configurable via `references/theme-schedule.json`. Default:

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
# View content history
python3 suggest_daily.py --history

# Generate draft for custom topic
python3 social_draft.py --topic "What is shared equity?" --category mortgage --theme hei_education

# Crawl single site
FIRECRAWL_API_KEY=<key> python3 crawl.py --url https://www.sweetjames.com

# Crawl all sites on schedule
FIRECRAWL_API_KEY=<key> python3 crawl.py --schedule

# Fetch industry news
BRAVE_API_KEY=<key> python3 news_fetch.py --topic "home equity investment California 2025"

# Generate image with custom prompt
GOOGLE_AI_API_KEY=<key> python3 generate_image.py --prompt "Attorney reviewing case files" --slug my-post
```

## Key Rules

- **No links/URLs in posts** — Facebook and X are standalone
- **No duplicate topics** within 30 days — enforced by content-calendar.json
- **Human approves before any post goes live**
- **Always photorealistic images** — no illustrations, no close-up faces
- **Human tone** — no emoji bullets, no generic CTAs
- **News first** — fetch news before generating suggestions
- Firecrawl: free=500 credits/month, paid=3K/month ($16)
- Google AI: billing required — ~$0.03-0.12/img

## Troubleshooting

| Issue | Fix |
|---|---|
| No suggestions | Run `news_fetch.py --auto` then `suggest_daily.py --record` |
| Image generation fails | Check `GOOGLE_AI_API_KEY` and billing at aistudio.google.com |
| Auto-post fails | Check browser has Facebook/X logged in |
| Facebook image upload stuck / Finder dialog open | NEVER click "Photo/video" button. Use hidden file input: `browser_evaluate('document.querySelector("input[type=file]").click()')` then `browser_file_upload`. Press Escape if dialog stuck. |
| X image upload fails | Use evaluate workaround — see `auto_post.py` |
| Duplicate topics | Auto-resets after 30 days |

## Documentation

- [README.md](README.md) — Beginner guide
- [QUICKSTART.md](QUICKSTART.md) — Quick reference
- [TOKEN-SETUP.md](TOKEN-SETUP.md) — How to get API keys
- [SETUP.md](SETUP.md) — Manual installation
- [WORKFLOW.md](WORKFLOW.md) — Detailed pipeline reference
