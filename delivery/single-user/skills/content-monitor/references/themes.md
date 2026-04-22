# Content Themes Reference

## Weekly Rotation

| Day | Category | Theme Key | Focus |
|---|---|---|---|
| Monday | personal-injury | `know_your_rights` | Legal education |
| Tuesday | mortgage | `hei_education` | HEI/equity products |
| Wednesday | personal-injury | `case_story` | Accident types + scenarios |
| Thursday | mortgage | `market_news` | Rates, trends, market |
| Friday | personal-injury | `faq` | Common questions |
| Saturday | mortgage | `tips` | Actionable advice |
| Sunday | both | `industry_news` | Cross-industry news |

## Topic Generation

Topics are NO LONGER hardcoded. They come from 3 sources (in priority order):

1. **Trending news** — fetched daily by `news_fetch.py --auto` via Brave Search
2. **Competitor content** — extracted from crawled sites by `crawl.py` → stored in `sites/{category}/.topics/`
3. **Evergreen fallback** — small pool in `suggest_daily.py`, used only when sources 1+2 are empty

The system generates 5 candidates per day. User picks which to use.

## Post Style Guidelines

### Tone: Human, not robotic

Write like a knowledgeable professional sharing insight with a friend — not like a marketing bot generating content.

**DO:**
- Start with a relatable scenario, surprising fact, or provocative question
- Use natural paragraph flow
- Vary sentence length — short punchy sentences mixed with longer explanatory ones
- Reference specific details (dollar amounts, timelines, jurisdiction names)
- Acknowledge nuance ("it depends", "in most cases", "there are exceptions")

**DON'T:**
- Start every post with an emoji
- Use emoji as bullet points (no checkmarks, no arrows, no warning signs as structure)
- Use the same post structure every day
- Include filler phrases ("Here's what you need to know", "Stay informed", "Knowledge is power")
- End with generic CTAs ("Don't navigate this alone")

### Structure Variation

The system rotates through 6 post structures automatically:

| Structure | Opens with | Best for |
|---|---|---|
| **Story** | A relatable scenario | know_your_rights, case_story |
| **Stat** | A surprising number | market_news, faq |
| **Question** | A provocative question | faq, hei_education |
| **Myth** | A common misconception | tips, know_your_rights |
| **News angle** | A recent headline | market_news, industry_news |
| **Direct** | Straight to the point | tips, hei_education |

### Hashtags

- **Facebook**: max 3 hashtags, on the last line
- **X/Twitter**: max 2 hashtags
- No hashtags in the body of the post
- Rotate hashtag sets by date (automatic)

### Emoji Policy

- Max 1 emoji per post (at the very start, if natural)
- No emoji as bullet points or structural elements
- No emoji in X/Twitter posts
- If a post reads better without emoji, skip it entirely

### Examples of Good vs Bad

**Bad (old style):**
```
🚨 Most accident victims don't know this —

**What to do in the first 24 hours after a car accident**

Here's what you need to know:

✅ You have the right to compensation
✅ Insurance companies are NOT on your side
✅ A free consultation costs you nothing

Don't navigate this alone. Protect your rights.

#PersonalInjury #AccidentAttorney #KnowYourRights #CaliforniaLaw #NevadaLaw
```

**Good (new style):**
```
You're driving home from work when someone runs a red light and slams into your car. You're shaken, confused, maybe hurt. What do you do next?

Most people make critical mistakes in the first few hours that can cost them their entire claim.

**What to do in the first 24 hours after a car accident**

The insurance company will call fast. They'll sound sympathetic. But their job is to settle for as little as possible — before you even know the full extent of your injuries.

Get the facts before you make any decisions. Your future self will thank you.

#PersonalInjury #CaliforniaLaw #KnowYourRights
```

## News Sources

News is fetched automatically by `news_fetch.py --auto` using Brave Search API. Key domains:

| Source | Focus |
|---|---|
| law.com/therecorder | CA legal news |
| housingwire.com | Mortgage/real estate |
| nationalmortgagenews.com | Mortgage industry |
| abovethelaw.com | Legal industry |
| inman.com | Real estate |
