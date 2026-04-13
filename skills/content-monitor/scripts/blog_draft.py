#!/usr/bin/env python3
"""
blog_draft.py - Generate full content drafts: blog article + social posts.

Takes a topic suggestion (from suggest_daily.py) and scraped competitor
content as inspiration, then produces:
  1. Blog article draft (for yoursite.com/blog/<slug>)
  2. Facebook post linking to the blog
  3. X/Twitter post linking to the blog
  4. Gemini image prompt
  5. Optional: news snippets to reference

Usage:
  python3 blog_draft.py --topic "What to do in the first 24 hours after a car accident"
  python3 blog_draft.py --from-calendar        # use today's suggestion from content-calendar.json
  python3 blog_draft.py --from-calendar --date 2026-04-10

Env:
  (optional) BRAVE_API_KEY — enriches with news context

Output:
  posts/drafts/<category>/<slug>-<date>.md  — complete content package
"""

import os
import os
import sys
import json
import argparse
import datetime
import re
import hashlib
import random
from pathlib import Path

WORKSPACE = Path(os.environ.get("CONTENT_MONITOR_WORKSPACE", str(Path.home() / ".openclaw" / "workspace")))
DRAFTS_DIR = WORKSPACE / "posts" / "drafts"
SITES_DIR = WORKSPACE / "sites"
NEWS_DIR = WORKSPACE / "news"
CALENDAR_FILE = WORKSPACE / "content-calendar.json"

YOUR_DOMAIN = "www.yoursite.com"  # REPLACE with actual domain

DRAFT_TEMPLATE = """\
---
title: {title}
slug: {slug}
blog_url: {blog_url}
category: {category}
theme: {theme}
date: {date}
status: draft
---

# Blog Article Draft

## Title
{title}

## Meta Description (SEO, max 160 chars)
{meta_description}

## Article Outline

{outline}

## Key Points to Cover

{key_points}

## Suggested News/Stats to Reference

{news_refs}

## Internal Link Suggestions

{internal_links}

---

# Facebook Post

{facebook}

---

# X / Twitter Post

{twitter}

---

# Image Prompt (Gemini / AI image generator)

{image_prompt}

---

# Publishing Checklist

- [ ] Expand outline into full article (~800-1200 words)
- [ ] Add 2-3 internal links to other blog posts
- [ ] Add meta title + description in CMS
- [ ] Generate image using the prompt above
- [ ] Schedule or publish at: {blog_url}
- [ ] Copy Facebook post → schedule on Facebook
- [ ] Copy X post → schedule on X/Twitter
- [ ] Move this file to posts/approved/ after review
"""


def slug_from_title(title):
    t = title.lower()
    t = re.sub(r'[^a-z0-9\s-]', '', t)
    t = re.sub(r'\s+', '-', t.strip())
    t = re.sub(r'-+', '-', t)
    return t[:80]


def topic_hash(topic):
    return hashlib.md5(topic.lower().strip().encode()).hexdigest()[:8]


def load_news_for_theme(theme, date_str):
    """Try to load news file for this theme/date."""
    news_file = NEWS_DIR / f"{date_str}-{theme}.json"
    if news_file.exists():
        items = json.loads(news_file.read_text())
        return items[:3]
    return []


def load_competitor_snippets(category, max_snippets=3):
    """Load short excerpts from competitor sites for inspiration."""
    cat_dir = SITES_DIR / category
    if not cat_dir.exists():
        return []
    files = list(cat_dir.glob("*.md"))
    snippets = []
    seed = random.Random(datetime.date.today().isoformat())
    seed.shuffle(files)
    for f in files[:max_snippets]:
        text = f.read_text()
        # Strip frontmatter
        if text.startswith("---"):
            end = text.find("---", 3)
            if end > 0:
                text = text[end + 3:].strip()
        # Clean markdown
        text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 50]
        if lines:
            snippets.append(lines[0][:200])
    return snippets


def build_outline(title, category, theme):
    """Build a structured article outline from title + theme."""
    outlines = {
        "know_your_rights": [
            "1. Introduction — why this matters right now",
            "2. The key right/rule explained simply",
            "3. Common mistakes people make",
            "4. Step-by-step what to do",
            "5. Real-world example or scenario",
            "6. When to consult an attorney",
            "7. Conclusion + CTA",
        ],
        "hei_education": [
            "1. Introduction — the problem this solves",
            "2. What is [topic] explained simply",
            "3. How it works step by step",
            "4. Pros and cons",
            "5. Who it's best for",
            "6. Common questions answered",
            "7. Conclusion + CTA",
        ],
        "case_story": [
            "1. The scenario (relatable situation)",
            "2. What the law says",
            "3. Key factors that affect the outcome",
            "4. What victims should do immediately",
            "5. How compensation is calculated",
            "6. Why professional help matters",
            "7. Conclusion + CTA",
        ],
        "market_news": [
            "1. The current market trend",
            "2. What it means for homeowners / consumers",
            "3. Data and statistics",
            "4. Expert perspectives",
            "5. Practical action steps",
            "6. Conclusion + CTA",
        ],
        "faq": [
            "1. Why people ask this question",
            "2. The short answer",
            "3. The detailed answer with nuance",
            "4. Related questions",
            "5. What to do next",
            "6. Conclusion + CTA",
        ],
        "tips": [
            "1. Introduction — why this matters",
            "2. Tip #1 with explanation",
            "3. Tip #2 with explanation",
            "4. Tip #3 with explanation",
            "5. Tip #4 with explanation",
            "6. Tip #5 with explanation",
            "7. Conclusion + CTA",
        ],
        "industry_news": [
            "1. The news/development explained",
            "2. Why it matters to consumers",
            "3. How it affects personal injury / home equity",
            "4. What to watch for",
            "5. Conclusion + CTA",
        ],
    }
    lines = outlines.get(theme, outlines["know_your_rights"])
    return "\n".join(lines)


def build_key_points(title, category):
    """Generate key points based on category."""
    if "injury" in category or "personal" in category:
        return (
            "- Explain the legal concept in plain English\n"
            "- Include California AND Nevada specifics where relevant\n"
            "- Use empathetic, non-jargon tone (audience = accident victims)\n"
            "- Include at least 1 actionable tip\n"
            "- Add CTA: free consultation at yoursite.com"
        )
    else:
        return (
            "- Explain the financial concept in plain English\n"
            "- Include real numbers/examples where possible\n"
            "- Compare options (HEI vs HELOC vs cash-out refi)\n"
            "- Highlight no-monthly-payment benefit if relevant\n"
            "- Add CTA: explore options at yoursite.com"
        )


def build_internal_links(category):
    """Suggest internal linking opportunities."""
    if "injury" in category or "personal" in category:
        return (
            "- /blog/what-to-do-after-car-accident\n"
            "- /blog/how-personal-injury-settlements-work\n"
            "- /blog/california-personal-injury-statute-of-limitations\n"
            "- /contact (for free consultation CTA)"
        )
    else:
        return (
            "- /blog/what-is-home-equity-investment\n"
            "- /blog/hei-vs-heloc-comparison\n"
            "- /blog/how-to-use-home-equity\n"
            "- /contact (for equity assessment CTA)"
        )


def build_meta_description(title, category):
    if "injury" in category or "personal" in category:
        return f"{title[:100]} | Expert guidance for accident victims in California & Nevada. Free consultation available."[:160]
    else:
        return f"{title[:100]} | Home equity solutions for homeowners. No monthly payments required."[:160]


def build_facebook(title, blog_url, category, news_refs):
    news_hook = ""
    if news_refs:
        news_hook = f"📰 In the news: {news_refs[0].get('title', '')}.\n\n"

    if "injury" in category or "personal" in category:
        hook = f"🚨 Know your rights.\n\n"
        body = f"{news_hook}We've put together a complete guide on: **{title}**\n\n"
        cta = (
            "If you or someone you know has been injured, don't navigate this alone.\n"
            f"Read the full guide → {blog_url}\n\n"
            "#PersonalInjury #InjuryLaw #CaliforniaLaw #NevadaLaw #AccidentAttorney #FreeConsultation"
        )
    else:
        hook = f"🏡 Your home equity is working harder than you think.\n\n"
        body = f"{news_hook}New on our blog: **{title}**\n\n"
        cta = (
            "Discover how homeowners are unlocking equity without taking on new debt.\n"
            f"Read the full guide → {blog_url}\n\n"
            "#HomeEquity #HEI #Mortgage #HomeEquityInvestment #RealEstate #NoMonthlyPayments"
        )
    return hook + body + cta


def build_twitter(title, blog_url, category):
    if "injury" in category or "personal" in category:
        post = f"Know your rights after an accident 🚨 {title} — full guide: {blog_url} #PersonalInjury #InjuryLaw"
    else:
        post = f"Your home equity, unlocked 🏡 {title} — read more: {blog_url} #HomeEquity #HEI #Mortgage"
    return post[:280]


def build_image_prompt(title, category, theme):
    if "injury" in category or "personal" in category:
        return (
            f"Editorial illustration for a personal injury law blog post about: '{title}'. "
            "Professional, trustworthy aesthetic. Deep blue and white color palette. "
            "No text in image. Style: modern legal/professional. "
            "Suggest: courthouse, scales of justice, supportive imagery, or accident recovery scene."
        )
    else:
        return (
            f"Editorial illustration for a home equity / mortgage blog post about: '{title}'. "
            "Professional, modern aesthetic. Warm tones, home/finance theme. "
            "No text in image. Style: real estate editorial. "
            "Suggest: modern home exterior, financial growth graphic, or family in front of house."
        )


def generate_draft(title, category, theme, date_str=None):
    date_str = date_str or datetime.date.today().isoformat()
    slug = slug_from_title(title)
    blog_url = f"https://{YOUR_DOMAIN}/blog/{slug}"

    news_refs = load_news_for_theme(theme, date_str)
    competitor_snippets = load_competitor_snippets(category)

    outline = build_outline(title, category, theme)
    key_points = build_key_points(title, category)
    internal_links = build_internal_links(category)
    meta_description = build_meta_description(title, category)
    facebook = build_facebook(title, blog_url, category, news_refs)
    twitter = build_twitter(title, blog_url, category)
    image_prompt = build_image_prompt(title, category, theme)

    # Format news refs for article
    if news_refs:
        news_text = "\n".join([f"- [{r['title']}]({r['url']}) — {r['snippet'][:100]}" for r in news_refs])
    else:
        news_text = "- No news fetched yet. Run: python3 news_fetch.py --theme " + theme

    draft = DRAFT_TEMPLATE.format(
        title=title,
        slug=slug,
        blog_url=blog_url,
        category=category,
        theme=theme,
        date=date_str,
        meta_description=meta_description,
        outline=outline,
        key_points=key_points,
        news_refs=news_text,
        internal_links=internal_links,
        facebook=facebook,
        twitter=twitter,
        image_prompt=image_prompt,
    )

    out_dir = DRAFTS_DIR / category
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{slug}-{date_str}.md"
    out_file.write_text(draft)
    print(f"  Draft → {out_file.relative_to(WORKSPACE)}")
    return out_file


def from_calendar(date_str=None):
    """Generate drafts from today's content calendar suggestions."""
    if not CALENDAR_FILE.exists():
        print("ERROR: content-calendar.json not found. Run suggest_daily.py --record first.", file=sys.stderr)
        sys.exit(1)

    cal = json.loads(CALENDAR_FILE.read_text())
    date_str = date_str or datetime.date.today().isoformat()
    todays = [p for p in cal.get("posts", []) if p.get("date") == date_str]

    if not todays:
        print(f"No suggestions found for {date_str} in calendar. Run suggest_daily.py --record first.")
        return

    for s in todays:
        generate_draft(
            title=s["title"],
            category=s["category"],
            theme=s["theme"],
            date_str=date_str,
        )


def main():
    parser = argparse.ArgumentParser(description="Generate blog + social draft from topic")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--topic", help="Topic/title to write about")
    group.add_argument("--from-calendar", action="store_true", help="Use today's calendar suggestions")
    parser.add_argument("--category", default="personal-injury",
                        choices=["personal-injury", "mortgage", "general"],
                        help="Content category (used with --topic)")
    parser.add_argument("--theme", default="know_your_rights",
                        help="Content theme (used with --topic)")
    parser.add_argument("--date", help="Date override (YYYY-MM-DD)")
    args = parser.parse_args()

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.from_calendar:
        from_calendar(args.date)
    else:
        generate_draft(args.topic, args.category, args.theme, args.date)


if __name__ == "__main__":
    main()
