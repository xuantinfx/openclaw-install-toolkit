# Content Monitor — First-Time Setup Wizard

**YOU MUST FOLLOW EVERY STEP BELOW IN ORDER. DO NOT SKIP ANY STEP. DO NOT IMPROVISE YOUR OWN SETUP FLOW.**

## When to run

On first use of the content-monitor skill, OR when the user says "setup content monitor", "configure content pipeline", or "set up posting".

Before starting: check if `~/.openclaw/workspace/.env-content-monitor` exists. If it does, ask: "Content Monitor is already configured. Do you want to re-run setup?" If no, skip.

## Agent behavior

This is a conversational setup. The agent asks the user questions in chat, collects answers, and performs actions (browser, file writes, cron) on the user's behalf.

**MANDATORY RULES:**
- Do NOT tell the user to run any scripts manually — the agent does everything
- Do NOT use LaunchAgent, crontab, or any OS-level scheduling — use CronCreate tool ONLY
- Do NOT skip the API keys step — keys must be saved to `~/.openclaw/workspace/.env-content-monitor`
- Do NOT skip the cron step — schedule must be created via CronCreate tool
- Do NOT finish setup until ALL 10 steps are completed
- Do NOT improvise steps that aren't listed here — follow this prompt exactly

---

## Step 1: Welcome

Say:

> Let's set up your Content Monitor. I'll walk you through a few quick steps:
>
> 1. Add websites to monitor
> 2. Log in to Facebook and X
> 3. Set your writing style (optional sample posts)
> 4. Configure weekly content themes
> 5. Enter API keys
> 6. Set your website domain
> 7. Schedule the daily pipeline
>
> Ready to start?

Wait for user confirmation.

---

## Step 2: Competitor Websites

Ask:

> What websites do you want to monitor for content ideas? These are competitor or industry sites that publish content in your niche.
>
> Paste the URLs (one per line), or say "use defaults" to keep the 56 pre-configured sites.

**If user provides URLs:**
1. Validate each URL (must be a domain or full URL)
2. For each URL, ask: "Is this personal injury, mortgage/HEI, or other?"
3. Append to `skills/content-monitor/references/sites.md` under a new section `## Added by Setup Wizard`
4. Confirm: "Added X sites. Total monitoring: Y sites."

**If user says "use defaults" or skips:**
- Confirm: "Using the default 56 competitor sites."

---

## Step 3: Social Media Login

Say:

> Now let's log in to your social media accounts so I can auto-post for you.
> I'll open a browser window — please log in to each platform.

**Facebook:**
1. Use Playwright MCP: navigate to `https://www.facebook.com/`
2. Say: "Please log in to your Facebook account in this browser window. Let me know when you're done."
3. Wait for user to confirm
4. Verify login: take a snapshot of the page and check for logged-in elements (profile picture, "What's on your mind?" composer, or similar)
5. If verified: "Facebook login confirmed."
6. If not verified: "I couldn't verify the login. Are you sure you're logged in?" — let user confirm manually

**X (Twitter):**
1. Use Playwright MCP: navigate to `https://x.com/`
2. Say: "Please log in to your X account in this browser window. Let me know when you're done."
3. Wait for user to confirm
4. Verify login: take a snapshot and check for compose button or profile elements
5. If verified: "X login confirmed."

**If user wants to skip either platform:**
- That's fine. Say: "You can log in later before auto-posting."

---

## Step 4: Sample Posts (Writing Style)

Ask:

> Do you have any sample posts you'd like me to learn your writing style from? This helps me match your tone when generating content.
>
> Options:
> 1. Paste sample post text
> 2. Share a URL to a post or page with your content
> 3. Skip — I'll use a professional default style

**If user pastes text:**
1. Save each sample to `skills/content-monitor/references/sample-posts.md` under `## User-Provided Samples`
2. Analyze the samples:
   - Tone (casual vs formal)
   - Average length
   - Emoji usage
   - Hashtag style
   - Sentence structure patterns
3. Generate `skills/content-monitor/references/writing-style.md` with the analysis
4. Confirm: "Got it! I'll write in a similar style. Here's what I noticed: [brief summary of tone/style]."
5. Ask: "Want to add more samples, or is this good?"

**If user provides a URL:**
1. Use Playwright MCP to navigate to the URL
2. Extract the post content from the page
3. Save and analyze as above

**If user skips:**
1. Keep the default `references/writing-style.md` as-is
2. Say: "Using the default professional style. You can add samples anytime by telling me."

---

## Step 5: Weekly Content Themes

Ask:

> Each day of the week has a content theme. Here's the current schedule:
>
> | Day | Category | Theme |
> |---|---|---|
> | Monday | Personal Injury | Know Your Rights |
> | Tuesday | Mortgage/HEI | HEI Education |
> | Wednesday | Personal Injury | Case Story |
> | Thursday | Mortgage/HEI | Market News |
> | Friday | Personal Injury | FAQ |
> | Saturday | Mortgage/HEI | Tips |
> | Sunday | Both | Industry News |
>
> Want to customize this? I can change any day's theme. Or say "keep defaults" to use this schedule.

**If user wants to customize:**

Go through each day one at a time:

> **Monday** — currently: Personal Injury / Know Your Rights
> What category and theme do you want for Monday?
> Categories: personal-injury, mortgage, both
> Themes: know_your_rights, hei_education, case_story, market_news, faq, tips, industry_news
> (Or press Enter to keep the current setting)

Repeat for Tuesday through Sunday.

The user can also describe themes in plain language — map them to the closest theme key:
- "legal education" or "rights" → `know_your_rights`
- "home equity" or "HEI" → `hei_education`
- "accident stories" or "cases" → `case_story`
- "market" or "rates" or "housing" → `market_news`
- "questions" or "FAQ" → `faq`
- "tips" or "advice" → `tips`
- "news" or "industry" → `industry_news`

After all 7 days are configured, save using:
```bash
python3 scripts/setup_wizard.py save-themes --schedule '{"0": {"category": "personal-injury", "theme": "know_your_rights"}, "1": {"category": "mortgage", "theme": "hei_education"}, ...}'
```

Show the final schedule and confirm:
> Here's your weekly schedule:
> [table]
> Look good?

**If user says "keep defaults":**
- Confirm: "Using the default theme schedule."
- No changes needed — the default `references/theme-schedule.json` is already in place.

---

## Step 6: API Keys

Say:

> Now I need a few API keys. I have a detailed guide at `TOKEN-SETUP.md` if you need help getting them.

Ask for each key one at a time:

**Firecrawl (required):**
> What's your Firecrawl API key? It starts with `fc-...`
> (Get one free at firecrawl.dev — 500 credits/month)

**Google AI / Gemini (required):**
> What's your Google AI API key? It starts with `AIzaSy...`
> (Get one at aistudio.google.com — billing must be enabled for image generation)

**Brave Search (optional):**
> Do you have a Brave Search API key? This enables trending news in your content.
> (Free at api.search.brave.com — 2,000 queries/month)
> Press Enter to skip.

After collecting all keys:
1. Create directory if needed: `mkdir -p ~/.openclaw/workspace/`
2. Write to `~/.openclaw/workspace/.env-content-monitor`:
   ```
   # Content Monitor API Keys
   export FIRECRAWL_API_KEY="<key>"
   export GOOGLE_AI_API_KEY="<key>"
   export BRAVE_API_KEY="<key>"
   ```
3. Set permissions: `chmod 600 ~/.openclaw/workspace/.env-content-monitor`
4. Confirm: "API keys saved securely."

---

## Step 7: Website Domain

Ask:

> What's your website domain? This is used for internal link suggestions.
> Example: www.mysite.com

1. Update `YOUR_DOMAIN` in `scripts/suggest_daily.py` and `scripts/blog_draft.py`
2. Confirm: "Domain set to [domain]."

---

## Step 8: Cron Schedule

Ask:

> What time should I run the daily content pipeline? I'll suggest topics and prepare drafts every morning.
>
> Default: 7:00 AM Asia/Saigon (Ho Chi Minh City time)
>
> Enter a time (e.g. "7:00 AM", "08:30", "6:00 AM") or press Enter for the default.

Also ask:

> What timezone? (Default: Asia/Saigon)

Then:
1. Convert time to cron expression (e.g. 7:00 AM → `0 7 * * *`)
2. Use `CronCreate` tool to create the cron job:
   - Name: `content-monitor-daily`
   - Expression: the cron expression
   - Timezone: user's timezone
   - Command/prompt: "Run the Content Monitor daily pipeline: fetch news, suggest topics, generate drafts, and send morning briefing."
3. Confirm: "Daily pipeline scheduled at [time] [timezone]. You'll get a morning briefing every day."

---

## Step 9: Initialize Workspace

Create the workspace structure silently (no need to ask the user):

```bash
mkdir -p ~/.openclaw/workspace/sites/{personal-injury,mortgage}
mkdir -p ~/.openclaw/workspace/news
mkdir -p ~/.openclaw/workspace/posts/drafts/{personal-injury,mortgage,general}
mkdir -p ~/.openclaw/workspace/posts/{images,approved,published}
mkdir -p ~/.openclaw/workspace/memory
```

Initialize data files if they don't exist:
- `~/.openclaw/workspace/content-calendar.json` → `{"posts": []}`
- `~/.openclaw/workspace/crawl-state.json` → `{"last_crawled": {}}`

---

## Step 10: Summary

Show the user a summary:

> Setup complete! Here's your configuration:
>
> - **Websites**: [count] sites monitored
> - **Facebook**: [connected / not connected]
> - **X (Twitter)**: [connected / not connected]
> - **Writing style**: [custom from N samples / default professional]
> - **Theme schedule**: [custom / default]
> - **API keys**: Firecrawl ✓, Google AI ✓, Brave [✓/✗]
> - **Domain**: [domain]
> - **Schedule**: [time] [timezone] daily
>
> **What happens next:**
> - Every morning at [time], I'll prepare content candidates
> - You pick which post to use
> - I'll generate an image and send it for review
> - After you approve, I'll post to Facebook and X
>
> Say "run content pipeline" anytime to trigger it manually.

---

## Rules

- **Never ask the user to run shell commands** — the agent does everything
- **Ask one question at a time** — don't overwhelm with multiple questions
- **Allow skipping any step** — nothing is truly mandatory (except API keys for the pipeline to work)
- **Validate inputs** — check URL format, key format (fc-..., AIzaSy...), time format
- **Be conversational** — this is a chat, not a form
- **Save progress** — if the user interrupts, the agent can resume from where it left off by checking which files already exist
- **All prompts in English** — user-facing text is in English
