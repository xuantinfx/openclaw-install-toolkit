#!/usr/bin/env python3
"""
crawl.py - Firecrawl scraper for content-monitor skill

Usage:
  python3 crawl.py --url https://example.com
  python3 crawl.py --url https://example.com --formats markdown
  python3 crawl.py --batch sites.txt
  python3 crawl.py --schedule   # crawl due sites based on schedule

Env:
  FIRECRAWL_API_KEY  (required)

Output:
  Writes scraped content to workspace/sites/<category>/<domain>.md
  Updates workspace/crawl-state.json with last crawl timestamps
"""

import os
import sys
import json
import argparse
import datetime
import re
import urllib.request
import urllib.error
from pathlib import Path

API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
API_URL = "https://api.firecrawl.dev/v1/scrape"

WORKSPACE = Path(__file__).parent.parent.parent.parent  # up to workspace root
SITES_DIR = WORKSPACE / "sites"
POSTS_DIR = WORKSPACE / "posts" / "drafts"
STATE_FILE = WORKSPACE / "crawl-state.json"

CATEGORIES = {
    "personal-injury": [
        "sweetjames.com", "dominguezfirm.com", "forthepeople.com", "ellisinjurylaw.com",
        "calljacob.com", "superwomansuperlawyer.com", "octrialattorneys.com",
        "calltheaccidentguys.com", "thebarnesfirm.com", "lawbrothers.com",
        "calldowntown.com", "larryhparker.com", "wilshirelaw.com",
        "callaccidentattorney.com", "westcoasttriallawyers.com", "sfalaw.com",
        "dklaw.com", "bdjinjurylawyers.com", "jacobyandmeyers.com", "themvp.com",
        "samandashlaw.com", "stevedimopoulos.com", "naqvilaw.com", "lernerandrowe.com",
        "corenalaw.com", "battlebornlasvegas.com", "ztlawgroup.com", "morrisinjurylaw.com",
        "richardharrislaw.com", "pacificwestinjury.com", "askadamskutner.com"
    ],
    "mortgage": [
        "splitero.com", "figure.com", "vestaequity.net", "point.com", "hometap.com",
        "unison.com", "jgwentworth.com", "amerisave.com", "splashfinancial.com",
        "newamericanfunding.com", "rocketmortgage.com", "lendingtree.com", "fundwell.com",
        "aven.com", "quickenloans.com", "achieve.com", "uwm.com", "pennymac.com",
        "loandepot.com", "fairway.com", "guildmortgage.com", "crosscountrymortgage.com",
        "bankrate.com", "ownup.com", "sagehomeloans.com"
    ]
}

# Sites with blogs get daily crawl; others weekly
BLOG_SITES = {
    "forthepeople.com", "jacobyandmeyers.com", "lernerandrowe.com", "richardharrislaw.com",
    "splitero.com", "figure.com", "point.com", "hometap.com", "unison.com",
    "jgwentworth.com", "newamericanfunding.com", "rocketmortgage.com", "lendingtree.com",
    "quickenloans.com", "achieve.com", "uwm.com", "pennymac.com", "loandepot.com",
    "fairway.com", "guildmortgage.com", "crosscountrymortgage.com", "bankrate.com",
    "ownup.com"
}


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_crawled": {}}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def is_due(domain, state):
    last = state["last_crawled"].get(domain)
    if not last:
        return True
    last_dt = datetime.datetime.fromisoformat(last)
    now = datetime.datetime.now(datetime.timezone.utc)
    interval = datetime.timedelta(days=1 if domain in BLOG_SITES else 7)
    return (now - last_dt) >= interval


def get_category(domain):
    for cat, domains in CATEGORIES.items():
        if domain in domains:
            return cat
    return "other"


def firecrawl_scrape(url):
    if not API_KEY:
        print("ERROR: FIRECRAWL_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    payload = json.dumps({
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
        "excludeTags": ["nav", "footer", "header", "script", "style", "iframe", "form"]
    }).encode()

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            if data.get("success"):
                return data.get("data", {}).get("markdown", "")
            else:
                print(f"  WARN: Firecrawl returned no success for {url}", file=sys.stderr)
                return None
    except urllib.error.HTTPError as e:
        print(f"  ERROR {e.code} scraping {url}: {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ERROR scraping {url}: {e}", file=sys.stderr)
        return None


def extract_topics(content, domain):
    """Extract article titles, headings, FAQ questions from crawled markdown."""
    topics = []
    if not content:
        return topics

    for line in content.split("\n"):
        line = line.strip()
        # Match markdown headings h1-h3
        m = re.match(r"^#{1,3}\s+(.+)$", line)
        if m:
            title = m.group(1).strip().strip("#").strip()
            # Skip very short or navigation-like headings
            if len(title) < 10 or title.lower() in ("menu", "home", "about", "contact", "blog", "faq", "footer"):
                continue
            # Classify by pattern
            lower = title.lower()
            if any(q in lower for q in ("how ", "what ", "when ", "why ", "can ", "do ", "does ", "should ", "is ", "are ")):
                topic_type = "faq"
            elif any(w in lower for w in ("steps", "tips", "ways", "guide", "checklist")):
                topic_type = "guide"
            else:
                topic_type = "article"
            topics.append({"title": title, "type": topic_type, "source": domain})

    # Deduplicate by title
    seen = set()
    unique = []
    for t in topics:
        key = t["title"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(t)

    return unique


def save_topics(domain, category, topics):
    """Save extracted topics to structured JSON for suggest_daily.py to consume."""
    topics_dir = SITES_DIR / category / ".topics"
    topics_dir.mkdir(parents=True, exist_ok=True)
    out_file = topics_dir / f"{domain}.json"
    data = {
        "domain": domain,
        "category": category,
        "crawled_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "count": len(topics),
        "topics": topics
    }
    out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    if topics:
        print(f"  Topics → {len(topics)} extracted from {domain}")


def save_content(domain, category, content, url):
    out_dir = SITES_DIR / category
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{domain}.md"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    header = f"---\nurl: {url}\ndomain: {domain}\ncategory: {category}\ncrawled_at: {now}\n---\n\n"
    out_file.write_text(header + (content or ""))
    print(f"  Saved → {out_file.relative_to(WORKSPACE)}")

    # Extract and save structured topics
    topics = extract_topics(content, domain)
    save_topics(domain, category, topics)


def crawl_url(url, force=False):
    domain = re.sub(r"^www\.", "", url.replace("https://", "").replace("http://", "").split("/")[0])
    category = get_category(domain)
    state = load_state()

    if not force and not is_due(domain, state):
        print(f"  SKIP {domain} (not due yet)")
        return

    print(f"  Crawling {url} ...")
    content = firecrawl_scrape(url)
    if content:
        save_content(domain, category, content, url)
        state["last_crawled"][domain] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_state(state)
    else:
        print(f"  FAILED {domain}")


def crawl_schedule(force=False):
    """Crawl all due sites based on schedule."""
    state = load_state()
    due = []
    for cat, domains in CATEGORIES.items():
        for domain in domains:
            if force or is_due(domain, state):
                due.append((cat, domain))

    if not due:
        print("No sites due for crawl.")
        return

    print(f"Sites due: {len(due)}")
    for cat, domain in due:
        url = f"https://www.{domain}"
        crawl_url(url, force=True)


def main():
    parser = argparse.ArgumentParser(description="Firecrawl scraper for content-monitor")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Single URL to crawl")
    group.add_argument("--batch", help="Text file with one URL per line")
    group.add_argument("--schedule", action="store_true", help="Crawl all due sites")
    parser.add_argument("--force", action="store_true", help="Ignore schedule, crawl anyway")
    args = parser.parse_args()

    SITES_DIR.mkdir(parents=True, exist_ok=True)
    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.url:
        crawl_url(args.url, force=args.force)
    elif args.batch:
        urls = Path(args.batch).read_text().splitlines()
        for url in urls:
            url = url.strip()
            if url and not url.startswith("#"):
                crawl_url(url, force=args.force)
    elif args.schedule:
        crawl_schedule(force=args.force)


if __name__ == "__main__":
    main()
