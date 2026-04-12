# Content Monitor — Setup Guide

## What is this?

A fully automated social media content pipeline for **personal injury law** and **mortgage/home equity** content targeting California & Nevada markets.

**What it does every morning (7AM):**
1. Suggests 2 unique content topics (no duplicates for 30 days)
2. Generates Facebook + X/Twitter posts (standalone, no links)
3. Sends you a briefing — you pick which post to use
4. Generates a photorealistic image (Google Gemini) only for your chosen post
5. Packages everything into a timestamped folder for easy posting

---

## Requirements

| Tool | Version | Notes |
|---|---|---|
| OpenClaw | Latest | https://openclaw.ai |
| Python | 3.9+ | Usually pre-installed on macOS |
| Firecrawl account | Free tier | 500 credits/month |
| Google AI account | Paid (billing enabled) | aistudio.google.com — Nano Banana 2 ~$0.12/img, Imagen 4 $0.03/img |

---

## Quick Install (New Machine)

```bash
# 1. Clone or copy this folder to your machine
# 2. Run setup script
cd content-monitor
chmod +x setup.sh
./setup.sh
```

The script will:
- Install the skill into OpenClaw
- Create workspace folder structure
- Save your API keys securely
- Set your website domain
- Run a quick pipeline test

---

## Manual Install (if setup.sh doesn't work)

### Step 1 — Install skill
```bash
cp -r content-monitor /opt/homebrew/lib/node_modules/openclaw/skills/
```

### Step 2 — Create workspace structure
```bash
WORKSPACE="$HOME/.openclaw/workspace"
mkdir -p $WORKSPACE/sites/{personal-injury,mortgage}
mkdir -p $WORKSPACE/news
mkdir -p $WORKSPACE/posts/{drafts/{personal-injury,mortgage,general},images,approved,published}
mkdir -p $WORKSPACE/memory
echo '{"posts": []}' > $WORKSPACE/content-calendar.json
echo '{"last_crawled": {}}' > $WORKSPACE/crawl-state.json
```

### Step 3 — Set your domain
Edit these 2 files and replace `www.yoursite.com`:
- `scripts/suggest_daily.py` → line: `YOUR_DOMAIN = "www.yoursite.com"`
- `scripts/blog_draft.py` → line: `YOUR_DOMAIN = "www.yoursite.com"`

### Step 4 — API keys
Create `~/.openclaw/workspace/.env-content-monitor`:
```bash
export FIRECRAWL_API_KEY="fc-your-key-here"
export GOOGLE_AI_API_KEY="AIzaSy-your-key-here"
export BRAVE_API_KEY="your-brave-key-here"   # optional
```

### Step 5 — Set up cron (via OpenClaw chat)
Tell your agent:
> "Set up the content-monitor daily cron at 7AM Asia/Saigon"

---

## Daily Workflow

```
7:00 AM → Agent runs pipeline → sends you briefing (text only)
         ↓
You reply: "1", "2", or "both"
         ↓
Agent generates image (Google Gemini)
  + sends image directly to Telegram for preview
  + sends full Facebook + X post text
         ↓
You reply: "approve"
         ↓
Files saved to: posts/approved/YYYY-MM-DD-HHMM/
  ├── post-slug-date.md    ← Facebook + X copy
  └── post-slug-date.jpg   ← 1080x1080 image
         ↓
You post manually to Facebook + X
         ↓
Tell agent: "published" → files move to posts/published/
```

---

## Workspace Structure

```
~/.openclaw/workspace/
├── sites/
│   ├── personal-injury/     ← scraped competitor content
│   └── mortgage/
├── news/                    ← industry news cache
├── posts/
│   ├── drafts/              ← agent-generated, awaiting your choice
│   ├── images/              ← temporary (moved to approved after pick)
│   ├── approved/
│   │   └── 2026-04-05-1604/ ← timestamped package (draft + image)
│   └── published/
│       └── 2026-04-05-1604/ ← archived after posting
├── content-calendar.json    ← 30-day topic tracker (prevents duplicates)
├── crawl-state.json         ← competitor crawl timestamps
└── .env-content-monitor     ← API keys (chmod 600)
```

---

## API Keys Reference

| Key | Where to get it | Cost |
|---|---|---|
| `FIRECRAWL_API_KEY` | firecrawl.dev → Dashboard | Free 500 credits/month |
| `GOOGLE_AI_API_KEY` | aistudio.google.com → API Keys (billing required) | Nano Banana 2 ~$0.12/img, Imagen 4 $0.03/img |
| `BRAVE_API_KEY` | api.search.brave.com | Free 2,000 queries/month |

---

## Competitor Sites Monitored

56 sites across 2 categories — see `references/sites.md` for full list.

**Personal Injury (CA & NV):** sweetjames.com, dominguezfirm.com, forthepeople.com, richardharrislaw.com, and 27 more.

**Mortgage / Home Equity:** splitero.com, hometap.com, point.com, rocketmortgage.com, lendingtree.com, and 20 more.

---

## Weekly Content Theme Rotation

| Day | Category | Theme |
|---|---|---|
| Monday | Personal Injury | Know Your Rights |
| Tuesday | Mortgage/HEI | HEI Education |
| Wednesday | Personal Injury | Case Story |
| Thursday | Mortgage/HEI | Market News |
| Friday | Personal Injury | FAQ |
| Saturday | Mortgage/HEI | Tips |
| Sunday | Both | Industry News |

Topics never repeat within 30 days.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Script not found | Run from workspace root or use full path |
| API key error | `source ~/.openclaw/workspace/.env-content-monitor` |
| Image generation fails | Check Google AI billing at aistudio.google.com |
| Duplicate topics | `suggest_daily.py --history` to see used topics |
| Need to reset calendar | Delete `content-calendar.json` (will recreate) |

---

## Support

- OpenClaw docs: https://docs.openclaw.ai
- Firecrawl docs: https://docs.firecrawl.dev
- Google AI docs: https://ai.google.dev/gemini-api/docs
