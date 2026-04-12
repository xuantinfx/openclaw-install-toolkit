# Content Monitor

An AI-powered content pipeline that monitors competitor websites, generates unique social media posts, creates photorealistic images, and auto-posts to Facebook and X (Twitter) — all managed by an AI agent through chat.

You don't need to know how to code. Just talk to the agent and it handles everything.

---

## What Does It Do?

Every morning, the agent:

1. **Scans competitor websites** in your industry for trending topics
2. **Fetches the latest news** relevant to your niche
3. **Suggests 3-5 unique topic ideas** (never repeats within 30 days)
4. **Writes Facebook and X posts** matching your writing style
5. **Generates a photorealistic image** using Google AI
6. **Sends you a preview** for approval
7. **Posts to Facebook and X** after you approve

All you do is pick which post you like and say "approve". The agent does the rest.

---

## How It Works (Simple Version)

```
Every morning:

  Agent: "Good morning! Here are today's content options:"
         Post 1 — Know Your Rights: What to do after a car accident
         Post 2 — Market News: California housing rates drop

  You:   "I like post 1"

  Agent: [generates image, shows preview]
         "Here's the post with image. Approve?"

  You:   "approve"

  Agent: [posts to Facebook and X automatically]
         "Done! Published to both platforms."
```

That's it. You just pick and approve.

---

## Getting Started

### What You Need

| Item | What it is | Cost |
|---|---|---|
| [OpenClaw](https://openclaw.ai) | The AI agent platform that runs this skill | — |
| [Firecrawl](https://www.firecrawl.dev/) account | Reads competitor websites | Free (500 pages/month) |
| [Google AI](https://aistudio.google.com/) account | Creates images for your posts | ~$0.03-0.12 per image |
| [Brave Search](https://api.search.brave.com/) account | Finds trending news (optional) | Free (2,000 searches/month) |

### Step 1: Get Your API Keys

You need API keys (like passwords) to connect to the services above. Don't worry — the agent will guide you, but here's a quick overview:

**Firecrawl** (reads competitor websites):
1. Go to [firecrawl.dev](https://www.firecrawl.dev/) and create a free account
2. Go to Dashboard → API Keys → Create API Key
3. Copy the key (starts with `fc-`)

**Google AI** (creates images):
1. Go to [aistudio.google.com](https://aistudio.google.com/)
2. Sign in with Google → click "Get API Key" → Create API Key
3. Copy the key (starts with `AIzaSy`)
4. **Important**: You need to [enable billing](https://console.cloud.google.com/billing) for image generation to work (you'll only be charged a few cents per image)

**Brave Search** (finds news — optional but recommended):
1. Go to [api.search.brave.com](https://api.search.brave.com/)
2. Create a free account → select the Free plan
3. Go to Dashboard → Generate API Key
4. Copy the key

See [TOKEN-SETUP.md](TOKEN-SETUP.md) for detailed step-by-step instructions with screenshots.

### Step 2: Run Setup

Open a chat with your OpenClaw agent and say:

> **"setup content monitor"**

The agent will walk you through everything:

1. **Websites** — "What competitor websites do you want to monitor?"
   - Give it URLs of competitors in your industry
   - Or say "use defaults" to use the 56 pre-configured sites

2. **Social media login** — "I'll open a browser for you to log in"
   - The agent opens a browser window
   - You log in to Facebook and X as normal
   - The agent saves your login session

3. **Writing style** — "Do you have any sample posts?"
   - Paste an example of a post you've written before
   - The agent learns your tone and style
   - Or skip this — it uses a clean professional style by default

4. **API keys** — "What's your Firecrawl key?"
   - Paste each API key when asked
   - The agent saves them securely

5. **Schedule** — "What time should I run the daily pipeline?"
   - Pick a time (default: 7:00 AM)
   - The agent sets up the daily schedule automatically

That's it! Setup takes about 5 minutes.

### Step 3: Use It Daily

After setup, the pipeline runs automatically every morning. You'll receive a message like:

```
Good morning! Here are today's content candidates:

Post 1 — Personal Injury | Know Your Rights | Source: news
Title: What California drivers don't know about uninsured motorist claims
[Preview of Facebook post...]
---
X: Most CA drivers carry uninsured motorist coverage but never use it...

Post 2 — Mortgage | Market News | Source: competitor
Title: Why home equity investments are surging in 2026
[Preview of Facebook post...]

Which post do you want to use today?
```

You reply with "1" or "2". The agent generates an image, shows you the full post for review, and after you say "approve", it posts to Facebook and X.

---

## Common Things You Can Say

| What you say | What happens |
|---|---|
| "setup content monitor" | Run the first-time setup wizard |
| "run content pipeline" | Trigger the daily pipeline manually (instead of waiting for the scheduled time) |
| "what should I post today" | Get today's content suggestions |
| "suggest today's content" | Same as above |
| "generate image" | Create an image for a specific post |
| "approve" | Approve a post for publishing |
| "crawl sites" | Re-scan competitor websites for fresh content |
| "content calendar" | See what topics were posted in the last 30 days |
| "morning briefing" | Get the daily content briefing |

---

## What Gets Posted

### Facebook Posts
- 150-400 words of valuable, educational content
- No links or URLs — the post stands on its own
- Professional but approachable tone
- 1 photorealistic image (1080x1080)
- 3 relevant hashtags at the end

### X (Twitter) Posts
- Max 280 characters
- One sharp, punchy insight
- No links, no emoji
- 2 hashtags

### Images
- Photorealistic photos (not illustrations or cartoons)
- Generated by Google AI — copyright-safe
- 1080x1080 pixels (square, optimal for both platforms)
- Match the topic (e.g., attorney in office for legal topics, suburban home for mortgage topics)

---

## Weekly Content Schedule

The agent rotates through different content themes each day:

| Day | Topic Area | Theme |
|---|---|---|
| Monday | Personal Injury | Know Your Rights |
| Tuesday | Mortgage / Home Equity | HEI Education |
| Wednesday | Personal Injury | Case Stories |
| Thursday | Mortgage / Home Equity | Market News |
| Friday | Personal Injury | FAQ |
| Saturday | Mortgage / Home Equity | Tips |
| Sunday | Both | Industry News |

Topics never repeat within 30 days.

---

## Frequently Asked Questions

### Do I need to know how to code?
No. Everything is done through chat with the agent. You just talk to it.

### How much does it cost to run?
- **Firecrawl**: Free tier covers normal usage (500 pages/month)
- **Google AI images**: About $0.03-0.12 per image (one image per day = ~$1-4/month)
- **Brave Search**: Free tier covers normal usage (2,000 queries/month)
- **Total**: Roughly $1-4/month for daily posting

### Can I customize the websites it monitors?
Yes. During setup, you provide your own list of competitor websites. You can also add more later by telling the agent "add these sites to monitor: [urls]".

### Can I change the posting schedule?
Yes. Tell the agent "change content schedule to 8:00 AM" or whatever time you prefer.

### What if I don't like the suggested posts?
Just say "suggest more" or "give me different options". The agent will generate new candidates from different angles.

### Can I edit the posts before they go live?
Yes. After the agent shows you the draft, you can say things like "make it shorter", "change the tone", or paste your own edited version. The agent will use your version.

### What if I don't have a Brave Search key?
The pipeline still works. It just won't include trending news in the topic suggestions. It will use competitor content and evergreen topics instead. The Brave key is optional but recommended for fresher content.

### Can I post to only Facebook or only X?
Yes. When approving, say "post to Facebook only" or "post to X only".

### How do I stop the daily pipeline?
Tell the agent "stop the content monitor cron" or "pause daily content".

### Can I use this for a different industry?
Yes, but you'll need to update the competitor websites and content themes. The default setup is for personal injury law and mortgage/home equity in California and Nevada.

---

## File Structure (For Reference)

You don't need to touch these files — the agent manages them. But if you're curious:

```
~/.openclaw/workspace/
├── sites/                    ← Scraped competitor content
├── news/                     ← Daily industry news cache
├── posts/
│   ├── drafts/               ← Posts waiting for your review
│   ├── images/               ← Generated images
│   ├── approved/             ← Posts you approved
│   └── published/            ← Posts that were published
├── content-calendar.json     ← Tracks topics (prevents repeats)
└── .env-content-monitor      ← Your API keys (private)
```

---

## Troubleshooting

| Problem | What to do |
|---|---|
| Agent says "no suggestions today" | Say "crawl sites" to refresh competitor data, then "run content pipeline" |
| Image generation fails | Check that your Google AI billing is enabled at [console.cloud.google.com/billing](https://console.cloud.google.com/billing) |
| Auto-posting doesn't work | Make sure you logged in to Facebook/X during setup. Say "setup content monitor" to redo the login step |
| Posts seem generic | Provide sample posts during setup so the agent learns your style. Say "setup content monitor" and go to the writing style step |
| Pipeline doesn't run in the morning | Say "check content monitor cron" to verify the schedule is set |

---

## More Documentation

- [QUICKSTART.md](QUICKSTART.md) — Quick reference for common commands
- [TOKEN-SETUP.md](TOKEN-SETUP.md) — Detailed API key setup guide
- [SKILL.md](SKILL.md) — Full technical reference
- [WORKFLOW.md](WORKFLOW.md) — Detailed pipeline and script documentation
