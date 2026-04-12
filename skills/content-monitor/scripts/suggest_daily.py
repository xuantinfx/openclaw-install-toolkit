#!/usr/bin/env python3
"""
suggest_daily.py - Daily content suggestion engine.

Generates unique topic ideas from competitor content analysis + trending news.
No hardcoded topic pools — topics are dynamic, data-driven, and timely.

Usage:
  python3 suggest_daily.py             # suggest today's topics
  python3 suggest_daily.py --record    # suggest + save to calendar
  python3 suggest_daily.py --date 2026-04-10
  python3 suggest_daily.py --history   # show last 30 days
  python3 suggest_daily.py --count 5   # more candidates to choose from

Output:
  Prints suggestions to stdout as JSON
  Updates workspace/content-calendar.json
"""

import json
import datetime
import argparse
import hashlib
import random
import re
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent.parent.parent
CALENDAR_FILE = WORKSPACE / "content-calendar.json"
SITES_DIR = WORKSPACE / "sites"
NEWS_DIR = WORKSPACE / "news"

# Weekly rotation schedule (day 0=Monday)
# Loaded from references/theme-schedule.json if available, otherwise defaults
SKILL_DIR = Path(__file__).parent.parent
THEME_SCHEDULE_FILE = SKILL_DIR / "references" / "theme-schedule.json"

DEFAULT_WEEKLY_ROTATION = {
    0: {"category": "personal-injury", "theme": "know_your_rights"},
    1: {"category": "mortgage",        "theme": "hei_education"},
    2: {"category": "personal-injury", "theme": "case_story"},
    3: {"category": "mortgage",        "theme": "market_news"},
    4: {"category": "personal-injury", "theme": "faq"},
    5: {"category": "mortgage",        "theme": "tips"},
    6: {"category": "both",            "theme": "industry_news"},
}


def load_weekly_rotation():
    if THEME_SCHEDULE_FILE.exists():
        try:
            data = json.loads(THEME_SCHEDULE_FILE.read_text())
            schedule = data.get("schedule", {})
            rotation = {}
            for day_str, config in schedule.items():
                rotation[int(day_str)] = {
                    "category": config.get("category", "both"),
                    "theme": config.get("theme", "industry_news"),
                }
            if rotation:
                return rotation
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    return DEFAULT_WEEKLY_ROTATION


WEEKLY_ROTATION = load_weekly_rotation()

# Evergreen fallback topics — ONLY used when competitor + news data is empty
FALLBACK_TOPICS = {
    "know_your_rights": [
        "What to do in the first 24 hours after a car accident",
        "Why you should never accept the first settlement offer",
        "Understanding uninsured motorist coverage in California",
    ],
    "hei_education": [
        "What is a Home Equity Investment (HEI) and how does it work?",
        "HEI vs HELOC: which is right for you?",
    ],
    "case_story": [
        "How victims of rideshare accidents can recover compensation",
    ],
    "market_news": [
        "Housing market update: what homeowners should know",
    ],
    "faq": [
        "How long does a personal injury case take?",
    ],
    "tips": [
        "5 tips for getting the best home equity deal",
    ],
    "industry_news": [
        "Consumer protection updates: what homeowners and accident victims should know",
    ],
}


def load_calendar():
    if CALENDAR_FILE.exists():
        return json.loads(CALENDAR_FILE.read_text())
    return {"posts": [], "used_topics": {}}


def save_calendar(cal):
    CALENDAR_FILE.write_text(json.dumps(cal, indent=2, ensure_ascii=False))


def get_used_hashes(cal, days=30):
    """Return set of topic hashes used in the last N days."""
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    used = set()
    for post in cal.get("posts", []):
        if post.get("date", "") >= cutoff:
            used.add(post.get("topic_hash", ""))
    return used


def topic_hash(topic):
    return hashlib.md5(topic.lower().strip().encode()).hexdigest()[:8]


def slug_from_title(title):
    title = title.lower()
    title = re.sub(r'[^a-z0-9\s-]', '', title)
    title = re.sub(r'\s+', '-', title.strip())
    title = re.sub(r'-+', '-', title)
    return title[:80]


# ---------------------------------------------------------------------------
# COMPETITOR TOPIC EXTRACTION
# ---------------------------------------------------------------------------

def load_competitor_topics(category):
    """Load extracted topics from .topics/ JSON files created by crawl.py."""
    topics = []
    categories_to_scan = [category] if category != "both" else ["personal-injury", "mortgage"]

    for cat in categories_to_scan:
        topics_dir = SITES_DIR / cat / ".topics"
        if not topics_dir.exists():
            continue
        for f in topics_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                for t in data.get("topics", []):
                    t["category"] = cat
                    topics.append(t)
            except (json.JSONDecodeError, KeyError):
                continue

    return topics


def load_competitor_raw(category):
    """Fallback: extract topics directly from raw markdown if .topics/ empty."""
    topics = []
    categories_to_scan = [category] if category != "both" else ["personal-injury", "mortgage"]

    for cat in categories_to_scan:
        cat_dir = SITES_DIR / cat
        if not cat_dir.exists():
            continue
        for f in cat_dir.glob("*.md"):
            content = f.read_text(errors="ignore")
            domain = f.stem
            for line in content.split("\n"):
                line = line.strip()
                m = re.match(r"^#{1,3}\s+(.+)$", line)
                if m:
                    title = m.group(1).strip().strip("#").strip()
                    if len(title) >= 15 and title.lower() not in ("menu", "home", "about", "contact", "blog"):
                        topics.append({"title": title, "type": "article", "source": domain, "category": cat})

    return topics


# ---------------------------------------------------------------------------
# NEWS TOPIC EXTRACTION
# ---------------------------------------------------------------------------

def load_news_topics(theme, date_str):
    """Load news results fetched by news_fetch.py."""
    news_file = NEWS_DIR / f"{date_str}-{theme}.json"
    if not news_file.exists():
        return []

    try:
        items = json.loads(news_file.read_text())
        return [
            {"title": item["title"], "snippet": item.get("snippet", ""), "source": item.get("source", "news"), "type": "news"}
            for item in items
            if item.get("title")
        ]
    except (json.JSONDecodeError, KeyError):
        return []


# ---------------------------------------------------------------------------
# TOPIC GENERATION (the core logic)
# ---------------------------------------------------------------------------

def generate_topics(category, theme, date_str, used_hashes, count=5):
    """Generate unique topic candidates from competitor data + news + fallback."""
    candidates = []

    # Source 1: News (highest priority — timely)
    news_topics = load_news_topics(theme, date_str)
    for nt in news_topics:
        # Reframe news title as a content angle
        angle = reframe_news_as_topic(nt["title"], theme)
        if angle and is_quality_topic(angle) and topic_hash(angle) not in used_hashes:
            candidates.append({
                "title": angle,
                "source_type": "news",
                "source": nt.get("source", ""),
                "original_headline": nt["title"],
                "snippet": nt.get("snippet", ""),
            })

    # Source 2: Competitor content gaps
    comp_topics = load_competitor_topics(category)
    if not comp_topics:
        comp_topics = load_competitor_raw(category)

    for ct in comp_topics:
        if not is_quality_topic(ct["title"]):
            continue
        if topic_hash(ct["title"]) not in used_hashes:
            candidates.append({
                "title": ct["title"],
                "source_type": "competitor",
                "source": ct.get("source", ""),
                "original_headline": "",
                "snippet": "",
            })

    # Source 3: Evergreen fallback (only if nothing else)
    if len(candidates) < count:
        fallback = FALLBACK_TOPICS.get(theme, [])
        for ft in fallback:
            if topic_hash(ft) not in used_hashes:
                candidates.append({
                    "title": ft,
                    "source_type": "evergreen",
                    "source": "fallback",
                    "original_headline": "",
                    "snippet": "",
                })

    # Deduplicate by topic hash
    seen = set()
    unique = []
    for c in candidates:
        h = topic_hash(c["title"])
        if h not in seen:
            seen.add(h)
            unique.append(c)

    # Sort: news first, then competitor, then evergreen
    priority = {"news": 0, "competitor": 1, "evergreen": 2}
    unique.sort(key=lambda x: priority.get(x["source_type"], 3))

    # Shuffle within each priority tier (so not always the same news article)
    rng = random.Random(date_str)
    result = []
    for tier in ["news", "competitor", "evergreen"]:
        tier_items = [c for c in unique if c["source_type"] == tier]
        rng.shuffle(tier_items)
        result.extend(tier_items)

    return result[:count]


# Generic CTA phrases to reject as low-quality topics
_JUNK_PHRASES = [
    "read why", "find answers", "contact us", "call us", "get started",
    "learn more", "sign up", "you decide", "subscribe", "click here",
    "apply now", "view all", "see more", "schedule a", "request a",
]

_PHONE_RE = re.compile(r"^[\d\s().+-]{7,}$")
_URL_RE   = re.compile(r"(https?://|www\.)|\.(com|net|org|io)(/?$|\.)", re.IGNORECASE)


def is_quality_topic(title: str) -> bool:
    """Return True if the title is a real content topic, not junk."""
    t = title.strip()
    if not t:
        return False
    # Phone numbers (digits, dashes, spaces, parens)
    if _PHONE_RE.match(t):
        return False
    # URL or bare domain
    if _URL_RE.search(t):
        return False
    # Too short (fewer than 6 words)
    if len(t.split()) < 6:
        return False
    # Generic CTA phrases
    tl = t.lower()
    if any(phrase in tl for phrase in _JUNK_PHRASES):
        return False
    return True


def reframe_news_as_topic(headline, theme):
    """Reframe a raw news headline into a content-appropriate topic title.
    Returns None if headline is not relevant enough."""
    headline = headline.strip()
    if not headline or len(headline) < 15:
        return None

    # Remove source prefixes like "Bloomberg: " or "Reuters - "
    headline = re.sub(r"^[\w\s]+:\s*", "", headline)
    headline = re.sub(r"^[\w\s]+-\s*", "", headline)

    # Remove trailing source attributions
    headline = re.sub(r"\s*[-|]\s*[\w\s.]+$", "", headline)

    if len(headline) < 15:
        return None

    return headline.strip()


# ---------------------------------------------------------------------------
# SUGGESTION OUTPUT
# ---------------------------------------------------------------------------

def suggest_for_date(date_str=None, count=5):
    """Suggest content topics for a given date."""
    if date_str:
        target = datetime.date.fromisoformat(date_str)
    else:
        target = datetime.date.today()
        date_str = target.isoformat()

    cal = load_calendar()
    used = get_used_hashes(cal)
    weekday = target.weekday()
    rotation = WEEKLY_ROTATION[weekday]
    category = rotation["category"]
    theme = rotation["theme"]

    topics = generate_topics(category, theme, date_str, used, count=count)

    suggestions = []
    for t in topics:
        cat = category if category != "both" else "general"
        suggestions.append({
            "date": date_str,
            "weekday": target.strftime("%A"),
            "theme": theme,
            "category": cat,
            "title": t["title"],
            "slug": slug_from_title(t["title"]),
            "topic_hash": topic_hash(t["title"]),
            "source_type": t["source_type"],
            "source": t["source"],
            "original_headline": t.get("original_headline", ""),
            "news_snippet": t.get("snippet", ""),
        })

    return suggestions


def record_used(suggestions):
    """Mark suggestions as used in calendar."""
    cal = load_calendar()
    for s in suggestions:
        if s["topic_hash"] not in {p.get("topic_hash") for p in cal["posts"]}:
            cal["posts"].append(s)
    save_calendar(cal)


def show_history(days=30):
    cal = load_calendar()
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    recent = [p for p in cal.get("posts", []) if p.get("date", "") >= cutoff]
    recent.sort(key=lambda x: x["date"], reverse=True)
    print(json.dumps(recent, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Daily content suggestion engine")
    parser.add_argument("--date", help="Date to suggest for (YYYY-MM-DD), default today")
    parser.add_argument("--count", type=int, default=5, help="Number of topic candidates (default 5)")
    parser.add_argument("--history", action="store_true", help="Show last 30 days of suggestions")
    parser.add_argument("--record", action="store_true", help="Record suggestions to calendar")
    args = parser.parse_args()

    if args.history:
        show_history()
        return

    suggestions = suggest_for_date(args.date, args.count)

    print(json.dumps(suggestions, indent=2))

    if args.record:
        record_used(suggestions)
        print(f"\nRecorded {len(suggestions)} suggestions to content-calendar.json")


if __name__ == "__main__":
    main()
