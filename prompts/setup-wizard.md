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
- **AFTER EVERY STEP: tell the user what was done, then ask if they want to continue to the next step**
- **NEVER go silent after completing a step** — always respond with a status + next step prompt
- **If a step fails: explain what went wrong and ask the user how to proceed (retry, skip, or abort)**

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

**Wait for user to say yes before proceeding.**

---

## Step 2: Competitor Websites

Ask:

> **Step 1/7 — Competitor Websites**
>
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

**After this step, say:**
> ✅ Websites configured. Ready for the next step — Social Media Login. Continue?

**Wait for user confirmation before proceeding to Step 3.**

---

## Step 3: Social Media Login

Say:

> **Step 2/7 — Social Media Login**
>
> Now let's log in to your social media accounts so I can auto-post for you.
> I'll open a browser window — please log in to each platform.
> You can skip this if you want to set it up later.

**Facebook:**
1. Use Playwright MCP: navigate to `https://www.facebook.com/`
2. Say: "I've opened Facebook in the browser. Please log in to your account and let me know when you're done."
3. Wait for user to confirm
4. Verify login: take a snapshot of the page and check for logged-in elements (profile picture, "What's on your mind?" composer, or similar)
5. If verified: "✅ Facebook login confirmed."
6. If not verified: "I couldn't verify the login. Are you sure you're logged in?" — let user confirm manually

**X (Twitter):**
1. Use Playwright MCP: navigate to `https://x.com/`
2. Say: "Now I've opened X (Twitter). Please log in and let me know when you're done."
3. Wait for user to confirm
4. Verify login: take a snapshot and check for compose button or profile elements
5. If verified: "✅ X login confirmed."

**If user wants to skip either platform:**
- That's fine. Say: "No problem. You can log in later before auto-posting."

**After this step, say:**
> ✅ Social media login done. [Facebook: connected/skipped] [X: connected/skipped]
> Next step — Writing Style. Continue?

**Wait for user confirmation before proceeding to Step 4.**

---

## Step 4: Sample Posts (Writing Style)

Ask:

> **Step 3/7 — Writing Style**
>
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

**After this step, say:**
> ✅ Writing style set [custom/default]. Next step — Weekly Content Themes. Continue?

**Wait for user confirmation before proceeding to Step 5.**

---

## Step 5: Weekly Content Themes

Ask:

> **Step 4/7 — Weekly Content Themes**
>
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
> (Or say "keep" to keep the current setting)

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
> Here's your updated weekly schedule:
> [table]
> Look good?

**If user says "keep defaults":**
- Confirm: "Using the default theme schedule."
- No changes needed — the default `references/theme-schedule.json` is already in place.

**After this step, say:**
> ✅ Theme schedule configured. Next step — API Keys. Continue?

**Wait for user confirmation before proceeding to Step 6.**

---

## Step 6: API Keys

Say:

> **Step 5/7 — API Keys**
>
> Now I need a few API keys to power the pipeline. I'll walk you through each one.
> (See TOKEN-SETUP.md for detailed instructions on how to get them.)

Ask for each key **one at a time**:

**Firecrawl (required):**
> What's your Firecrawl API key? It starts with `fc-...`
> (Get one free at firecrawl.dev — 500 credits/month)

Wait for user to provide the key.

**Google AI / Gemini (required):**
> What's your Google AI API key? It starts with `AIzaSy...`
> (Get one at aistudio.google.com — billing must be enabled for image generation)

Wait for user to provide the key.

**Brave Search (optional):**
> Do you have a Brave Search API key? This enables trending news in your content.
> (Free at api.search.brave.com — 2,000 queries/month)
> Say "skip" if you don't have one.

Wait for user to provide or skip.

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

**After this step, say:**
> ✅ API keys saved securely.
> - Firecrawl: ✓
> - Google AI: ✓
> - Brave Search: [✓ / skipped]
>
> Next step — Website Domain. Continue?

**Wait for user confirmation before proceeding to Step 7.**

---

## Step 7: Website Domain

Ask:

> **Step 6/7 — Website Domain**
>
> What's your website domain? This is used for internal link suggestions in content.
> Example: www.mysite.com
> (Say "skip" if you don't have one yet.)

1. If user provides a domain: update `YOUR_DOMAIN` in `scripts/suggest_daily.py` and `scripts/blog_draft.py`
2. If user skips: keep the placeholder

**After this step, say:**
> ✅ Domain set to [domain / placeholder]. Last step — Schedule. Continue?

**Wait for user confirmation before proceeding to Step 8.**

---

## Step 8: Cron Schedule

Ask:

> **Step 7/7 — Daily Schedule**
>
> What time should I run the daily content pipeline? I'll suggest topics and prepare drafts every morning.
>
> Default: 7:00 AM (Asia/Saigon timezone)
>
> Enter a time (e.g. "7:00 AM", "08:30", "6:00 AM") or say "default" for 7:00 AM.

Wait for user to answer.

Then ask:

> What timezone? (Default: Asia/Saigon)

Wait for user to answer.

Then:
1. Convert time to cron expression (e.g. 7:00 AM → `0 7 * * *`)
2. Use `CronCreate` tool to create the cron job:
   - Name: `content-monitor-daily`
   - Expression: the cron expression
   - Timezone: user's timezone
   - Command/prompt: "Run the Content Monitor daily pipeline: fetch news, suggest topics, generate drafts, and send morning briefing."
3. Confirm the cron was created successfully.

**After this step, say:**
> ✅ Daily pipeline scheduled at [time] [timezone].
>
> Finishing up — let me initialize the workspace...

**Proceed directly to Step 9 (no confirmation needed — it's automatic).**

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

**Proceed directly to Step 10.**

---

## Step 10: Summary

Show the user a complete summary:

> 🎉 **Setup complete!** Here's your configuration:
>
> | Setting | Value |
> |---|---|
> | Websites | [count] sites monitored |
> | Facebook | [connected / not connected] |
> | X (Twitter) | [connected / not connected] |
> | Writing style | [custom from N samples / default] |
> | Theme schedule | [custom / default] |
> | Firecrawl key | ✓ saved |
> | Google AI key | ✓ saved |
> | Brave Search key | [✓ saved / not set] |
> | Domain | [domain] |
> | Daily schedule | [time] [timezone] |
>
> **What happens next:**
> 1. Every morning at [time], I'll prepare content candidates and send you a briefing
> 2. You pick which post to use (reply with the number)
> 3. I'll generate an image and send it for review
> 4. After you approve, I'll post to Facebook and X
>
> **You can also say these anytime:**
> - "run content pipeline" — trigger the pipeline now
> - "what should I post today" — get today's suggestions
> - "crawl sites" — refresh competitor data
> - "content calendar" — see recent topics
>
> Want me to run the pipeline now so you can see it in action?

**Wait for user response.** If they say yes, run the pipeline. If no, done.

---

## Rules

- **AFTER EVERY STEP: confirm what was done + ask to continue** — NEVER go silent
- **If something fails: explain the error and ask how to proceed** — don't just stop
- **Never ask the user to run shell commands** — the agent does everything
- **Ask one question at a time** — don't overwhelm with multiple questions
- **Allow skipping any step** — nothing is truly mandatory (except API keys for the pipeline to work)
- **Validate inputs** — check URL format, key format (fc-..., AIzaSy...), time format
- **Be conversational** — this is a chat, not a form
- **Save progress** — if the user interrupts, the agent can resume from where it left off by checking which files already exist
- **All prompts in English** — user-facing text is in English
- **Show step progress** — every step message should include "Step X/7" so user knows where they are
