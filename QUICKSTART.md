# Content Monitor — Quick Start Guide

## First Time Setup

Just tell the agent:

> "setup content monitor"

The agent walks you through everything in chat:
1. Adding competitor websites to monitor
2. Opening the browser for you to log in to Facebook and X
3. Providing sample posts (optional — sets your writing style)
4. Entering API keys (see [TOKEN-SETUP.md](TOKEN-SETUP.md) for how to get them)
5. Setting your website domain
6. Scheduling the daily cron job

No manual commands needed — the agent handles all setup.

### Manual Setup (Alternative)

```bash
chmod +x setup.sh
./setup.sh
```

See [SETUP.md](SETUP.md) for detailed manual instructions.

---

## Daily Workflow

Once set up, the pipeline runs automatically every morning:

```
Morning (auto)          You                         Agent
─────────────────────────────────────────────────────────────
Fetch news              ·                           ·
Suggest topics          ·                           ·
Generate drafts         ·                           ·
Send briefing ────────→ Read briefing               ·
                        Reply "1" or "2" ─────────→ ·
                        ·                           Generate image
                        ·                     ←──── Send preview
                        Reply "approve" ──────────→ ·
                        ·                           Post to Facebook
                        ·                           Post to X
                        ·                     ←──── Done!
```

---

## Common Commands

### Daily Pipeline (Manual Run)

```bash
# Run the full pipeline manually
python3 scripts/news_fetch.py --auto
python3 scripts/suggest_daily.py --record
python3 scripts/social_draft.py --from-calendar
```

### Crawl Competitor Sites

```bash
# Crawl all sites due for update
FIRECRAWL_API_KEY=<key> python3 scripts/crawl.py --schedule

# Force crawl all sites (first-time or refresh)
FIRECRAWL_API_KEY=<key> python3 scripts/crawl.py --schedule --force

# Crawl a single site
FIRECRAWL_API_KEY=<key> python3 scripts/crawl.py --url https://www.example.com
```

### Generate Image

```bash
# Generate image for a specific draft
GOOGLE_AI_API_KEY=<key> python3 scripts/generate_image.py --draft posts/drafts/<category>/<slug>.md

# Custom image prompt
GOOGLE_AI_API_KEY=<key> python3 scripts/generate_image.py --prompt "Attorney in office" --slug my-post --category personal-injury --theme faq
```

### Content Calendar

```bash
# View last 30 days of posted topics
python3 scripts/suggest_daily.py --history

# Generate more topic candidates
python3 scripts/suggest_daily.py --count 5
```

### Approve & Post

```bash
# Approve a draft (moves to approved/)
python3 scripts/approve_post.py --draft <path>

# Approve + auto-post via browser
python3 scripts/approve_post.py --draft <path> --auto-post

# Dry run (fill content but don't click publish)
python3 scripts/approve_post.py --draft <path> --auto-post --dry-run

# Mark as published (moves to published/)
python3 scripts/approve_post.py --publish posts/approved/<folder>
```

### News Fetching

```bash
# Fetch news for today's theme (auto-detects day)
BRAVE_API_KEY=<key> python3 scripts/news_fetch.py --auto

# Fetch news for a specific topic
BRAVE_API_KEY=<key> python3 scripts/news_fetch.py --topic "home equity California 2025"
```

---

## Key Files

| File | Purpose |
|---|---|
| `~/.openclaw/workspace/.env-content-monitor` | API keys (chmod 600) |
| `~/.openclaw/workspace/content-calendar.json` | 30-day topic history |
| `~/.openclaw/workspace/crawl-state.json` | Crawl timestamps per site |
| `~/.openclaw/workspace/posts/drafts/` | Drafts awaiting review |
| `~/.openclaw/workspace/posts/approved/` | Ready to post |
| `~/.openclaw/workspace/posts/published/` | Archive |
| `references/sites.md` | List of monitored competitor sites |
| `references/themes.md` | Weekly theme rotation + style guidelines |
| `references/writing-style.md` | Your custom writing style (from setup wizard) |
| `references/sample-posts.md` | Sample posts you provided |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| No suggestions generated | Run `news_fetch.py --auto` then `suggest_daily.py --record` |
| Image generation fails | Check `GOOGLE_AI_API_KEY` + billing at aistudio.google.com |
| Firecrawl rate limit | Use `--url` for single sites; avoid `--force` daily |
| Duplicate topics | Auto-resets after 30 days; check `suggest_daily.py --history` |
| Auto-post fails | Ensure Chrome relay active + logged in to Facebook/X |
| X image upload fails | See SKILL.md troubleshooting for the `evaluate` workaround |
| API key not found | Run `source ~/.openclaw/workspace/.env-content-monitor` |

---

## More Info

- [SKILL.md](SKILL.md) — Full skill reference
- [TOKEN-SETUP.md](TOKEN-SETUP.md) — How to get API keys
- [SETUP.md](SETUP.md) — Manual installation guide
- [WORKFLOW.md](WORKFLOW.md) — Detailed script reference
