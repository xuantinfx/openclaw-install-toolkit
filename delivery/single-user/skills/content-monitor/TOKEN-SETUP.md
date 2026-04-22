# API Token Setup Guide

This guide walks you through getting all the API keys needed to run the Content Monitor pipeline.

---

## 1. Google AI API Key (Required)

Used for: **Image generation** (Nano Banana 2 / Imagen 4)

**Cost**: Billing must be enabled. Nano Banana 2 ~$0.12/img, Imagen 4 $0.03/img, Imagen 4 Fast $0.02/img.

### Steps

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click **"Get API Key"** in the left sidebar
4. Click **"Create API Key"**
5. Select an existing Google Cloud project, or click **"Create API key in new project"**
6. Copy the generated key — it starts with `AIzaSy...`

### Enable Billing (Required for Image Generation)

Image generation models require a Google Cloud billing account:

1. Go to [Google Cloud Console](https://console.cloud.google.com/billing)
2. Click **"Link a billing account"** (or create one if you don't have any)
3. Add a payment method (credit/debit card)
4. Link the billing account to the project you created the API key in

### Verify

```bash
# Test with a simple text generation (free)
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY" | head -5
```

If you see a JSON response with model names, the key is working.

**Env var**: `GOOGLE_AI_API_KEY`

---

## 2. Firecrawl API Key (Required)

Used for: **Crawling competitor websites** (extracting content + topics)

**Cost**: Free tier = 500 credits/month. Paid = 3,000 credits/month ($16/month).

### Steps

1. Go to [Firecrawl](https://www.firecrawl.dev/)
2. Click **"Sign Up"** or **"Get Started"**
3. Create an account (GitHub or email)
4. After login, go to **Dashboard** → **API Keys**
5. Click **"Create API Key"**
6. Copy the key — it starts with `fc-...`

### Free Tier Limits

- 500 credits/month (1 page = 1 credit)
- The skill monitors 56 sites, most crawled weekly
- Typical monthly usage: ~300-400 credits (fits free tier)

### Verify

```bash
curl -s -X POST "https://api.firecrawl.dev/v1/scrape" \
  -H "Authorization: Bearer fc-YOUR-KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "formats": ["markdown"]}' | head -5
```

**Env var**: `FIRECRAWL_API_KEY`

---

## 3. Brave Search API Key (Optional but Recommended)

Used for: **Fetching trending industry news** daily to enrich content topics.

**Cost**: Free tier = 2,000 queries/month (more than enough — pipeline uses ~30/month).

### Steps

1. Go to [Brave Search API](https://api.search.brave.com/)
2. Click **"Get Started for Free"**
3. Create an account
4. After login, go to **Dashboard** → **API Keys**
5. Select the **"Free"** plan (2,000 queries/month)
6. Click **"Generate API Key"**
7. Copy the key

### What Happens Without This Key

- The pipeline still works — it falls back to competitor content and evergreen topics
- But news-based posts (trending angles, timely content) won't be available
- Recommended: get the free key, it takes 2 minutes

### Verify

```bash
curl -s "https://api.search.brave.com/res/v1/web/search?q=test" \
  -H "X-Subscription-Token: YOUR-BRAVE-KEY" | head -5
```

**Env var**: `BRAVE_API_KEY`

---

## 4. Google Custom Search API (Alternative to Brave)

If you prefer Google over Brave for news fetching, you can use Google Custom Search.

**Cost**: Free = 100 queries/day (3,000/month). More than enough.

### Steps

1. Go to [Google Custom Search](https://programmablesearchengine.google.com/)
2. Click **"Add"** to create a new search engine
3. Under "Sites to search", select **"Search the entire web"**
4. Give it a name (e.g., "Content Monitor")
5. Click **"Create"**
6. Copy the **Search Engine ID** (cx parameter)

Then get an API key:

7. Go to [Google Cloud Console → APIs](https://console.cloud.google.com/apis/credentials)
8. Click **"Create Credentials"** → **"API Key"**
9. Copy the key
10. Enable the **"Custom Search API"**: Go to [API Library](https://console.cloud.google.com/apis/library/customsearch.googleapis.com) → click **"Enable"**

### Verify

```bash
curl -s "https://www.googleapis.com/customsearch/v1?key=YOUR_KEY&cx=YOUR_CX&q=test" | head -5
```

**Env vars**: `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_CX`

---

## Summary

| Key | Required | Cost | Env Var |
|---|---|---|---|
| Google AI (Gemini) | Yes | Pay per image (~$0.03-0.12) | `GOOGLE_AI_API_KEY` |
| Firecrawl | Yes | Free 500 credits/month | `FIRECRAWL_API_KEY` |
| Brave Search | Recommended | Free 2,000 queries/month | `BRAVE_API_KEY` |
| Google Custom Search | Optional (alt to Brave) | Free 100 queries/day | `GOOGLE_SEARCH_API_KEY` + `GOOGLE_SEARCH_CX` |

## Saving Your Keys

After getting all keys, save them to `~/.openclaw/workspace/.env-content-monitor`:

```bash
export FIRECRAWL_API_KEY="fc-your-key"
export GOOGLE_AI_API_KEY="AIzaSy-your-key"
export BRAVE_API_KEY="your-brave-key"
# Optional: Google Custom Search (alternative to Brave)
# export GOOGLE_SEARCH_API_KEY="your-key"
# export GOOGLE_SEARCH_CX="your-cx"
```

Or run the setup wizard which handles this automatically:

```bash
python3 scripts/setup_wizard.py
```
