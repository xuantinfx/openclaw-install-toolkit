#!/usr/bin/env python3
"""
news_fetch.py - Fetch industry news for personal injury and mortgage/HEI topics.

Uses Brave Search API to find recent news relevant to the daily content theme.
Results are used to add timeliness to blog/social drafts.

Usage:
  python3 news_fetch.py --topic "home equity investment"
  python3 news_fetch.py --theme market_news
  python3 news_fetch.py --auto              # fetch news for today's theme automatically
  python3 news_fetch.py --date 2026-04-10   # fetch news relevant to that day's theme

Env:
  BRAVE_API_KEY  (required) — get free key at https://api.search.brave.com

Output:
  JSON + MD saved to workspace/news/<date>-<theme>.json and .md
"""

import os
import gzip
import io
import os
import sys
import json
import argparse
import datetime
import urllib.request
import urllib.parse
from pathlib import Path

WORKSPACE = Path(os.environ.get("CONTENT_MONITOR_WORKSPACE", str(Path.home() / ".openclaw" / "workspace")))
NEWS_DIR = WORKSPACE / "news"

BRAVE_API_URL = "https://api.search.brave.com/res/v1/news/search"

# Dynamic year — never hardcoded
CURRENT_YEAR = datetime.date.today().year

THEME_QUERIES = {
    "know_your_rights": f"personal injury law California Nevada {CURRENT_YEAR}",
    "hei_education":    f"home equity investment HEI {CURRENT_YEAR}",
    "case_story":       f"personal injury lawsuit settlement verdict {CURRENT_YEAR}",
    "market_news":      f"mortgage home equity market trends {CURRENT_YEAR}",
    "faq":              f"personal injury attorney common questions {CURRENT_YEAR}",
    "tips":             f"home equity loan tips homeowner {CURRENT_YEAR}",
    "industry_news":    f"personal injury mortgage legal financial news {CURRENT_YEAR}",
}

# Weekly rotation — loaded from config file if available
SKILL_DIR = Path(__file__).parent.parent
THEME_SCHEDULE_FILE = SKILL_DIR / "references" / "theme-schedule.json"

DEFAULT_WEEKLY_ROTATION = {
    0: "know_your_rights",   # Monday
    1: "hei_education",      # Tuesday
    2: "case_story",         # Wednesday
    3: "market_news",        # Thursday
    4: "faq",                # Friday
    5: "tips",               # Saturday
    6: "industry_news",      # Sunday
}


def load_weekly_rotation():
    if THEME_SCHEDULE_FILE.exists():
        try:
            data = json.loads(THEME_SCHEDULE_FILE.read_text())
            schedule = data.get("schedule", {})
            rotation = {}
            for day_str, config in schedule.items():
                rotation[int(day_str)] = config.get("theme", "industry_news")
            if rotation:
                return rotation
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    return DEFAULT_WEEKLY_ROTATION


WEEKLY_ROTATION = load_weekly_rotation()


def brave_search(query, count=10, freshness="pd"):
    """Search Brave News API. freshness: pd=past day, pw=past week."""
    api_key = os.environ.get("BRAVE_API_KEY", "")
    if not api_key:
        print("WARN: BRAVE_API_KEY not set — skipping news fetch", file=sys.stderr)
        return []

    params = urllib.parse.urlencode({
        "q": query,
        "count": count,
        "freshness": freshness,
        "text_decorations": False,
    })
    url = f"{BRAVE_API_URL}?{params}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            # Decompress gzip if needed
            if resp.headers.get("Content-Encoding") == "gzip" or (raw[:2] == b"\x1f\x8b"):
                raw = gzip.decompress(raw)
            data = json.loads(raw.decode("utf-8"))
            results = []
            for item in data.get("results", []):
                title = item.get("title", "").strip()
                snippet = item.get("description", "").strip()
                if not title:
                    continue
                results.append({
                    "title": title,
                    "url": item.get("url", ""),
                    "snippet": snippet,
                    "published": item.get("age", ""),
                    "source": item.get("meta_url", {}).get("netloc", ""),
                    "relevance": score_relevance(title, snippet, query),
                })
            # Sort by relevance score descending
            results.sort(key=lambda x: x["relevance"], reverse=True)
            return results
    except Exception as e:
        print(f"WARN: News fetch failed: {e}", file=sys.stderr)
        return []


def score_relevance(title, snippet, query):
    """Score how relevant a result is to the query. Higher = better."""
    text = (title + " " + snippet).lower()
    keywords = [w.lower() for w in query.split() if len(w) > 3]
    if not keywords:
        return 0
    matches = sum(1 for kw in keywords if kw in text)
    return round(matches / len(keywords), 2)


def results_to_markdown(results, theme, date_str):
    """Convert results to human-readable markdown summary."""
    lines = [
        f"# News: {theme}",
        f"\n> Date: {date_str}",
        f"> Results: {len(results)}",
        ""
    ]
    for i, r in enumerate(results, 1):
        lines.append(f"### {i}. {r['title']}")
        lines.append(f"- **Source**: {r['source']}")
        lines.append(f"- **Published**: {r['published']}")
        lines.append(f"- **Relevance**: {r['relevance']}")
        if r['snippet']:
            lines.append(f"- {r['snippet']}")
        lines.append("")
    return "\n".join(lines)


def save_results(results, theme, date_str):
    """Save results as both JSON and MD."""
    NEWS_DIR.mkdir(parents=True, exist_ok=True)

    # JSON (machine-readable)
    json_file = NEWS_DIR / f"{date_str}-{theme}.json"
    json_file.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    # Markdown (human-readable)
    md_file = NEWS_DIR / f"{date_str}-{theme}.md"
    md_file.write_text(results_to_markdown(results, theme, date_str))

    print(f"Saved {len(results)} news items → {json_file.name} + {md_file.name}")
    return results


def fetch_for_theme(theme, date_str=None, freshness="pd"):
    query = THEME_QUERIES.get(theme, f"personal injury mortgage news {CURRENT_YEAR}")
    results = brave_search(query, count=10, freshness=freshness)
    date_str = date_str or datetime.date.today().isoformat()
    return save_results(results, theme, date_str)


def fetch_for_topic(topic, date_str=None, freshness="pd"):
    results = brave_search(topic, count=10, freshness=freshness)
    date_str = date_str or datetime.date.today().isoformat()
    safe = topic.lower().replace(" ", "-")[:40]
    return save_results(results, safe, date_str)


def fetch_auto(date_str=None):
    """Automatically fetch news for today's theme based on weekly rotation."""
    date_str = date_str or datetime.date.today().isoformat()
    target_date = datetime.date.fromisoformat(date_str)
    weekday = target_date.weekday()
    theme = WEEKLY_ROTATION.get(weekday, "industry_news")

    print(f"Auto mode: {date_str} ({target_date.strftime('%A')}) → theme: {theme}")

    # Fetch with past-day freshness first, fall back to past-week if few results
    results = fetch_for_theme(theme, date_str, freshness="pd")
    if len(results) < 3:
        print(f"Only {len(results)} results with daily freshness, expanding to past week...")
        results = fetch_for_theme(theme, date_str, freshness="pw")

    return results


def main():
    parser = argparse.ArgumentParser(description="Fetch industry news for content theming")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--topic", help="Free-text topic to search")
    group.add_argument("--theme", choices=list(THEME_QUERIES.keys()), help="Predefined theme")
    group.add_argument("--auto", action="store_true", help="Auto-detect today's theme and fetch")
    parser.add_argument("--date", help="Date label for output file (YYYY-MM-DD)")
    parser.add_argument("--freshness", choices=["pd", "pw", "pm"], default="pd",
                        help="Result freshness: pd=past day, pw=past week, pm=past month")
    args = parser.parse_args()

    if args.auto:
        results = fetch_auto(args.date)
    elif args.topic:
        results = fetch_for_topic(args.topic, args.date, args.freshness)
    else:
        results = fetch_for_theme(args.theme, args.date, args.freshness)

    if not results:
        print("No news found.", file=sys.stderr)


if __name__ == "__main__":
    main()
