#!/usr/bin/env python3
"""
draft_post.py - Generate social media draft posts from scraped site content.

Usage:
  python3 draft_post.py --file sites/personal-injury/sweetjames.com.md
  python3 draft_post.py --all                  # process all unprocessed site files
  python3 draft_post.py --category mortgage    # process one category

Output format per draft:
  posts/drafts/<category>/<domain>-<YYYY-MM-DD>.md

Draft file contains:
  - Facebook post (max 400 words, conversational)
  - X/Twitter post (max 280 chars)
  - Suggested image prompt for Gemini (when API available)
  - Source URL and metadata
"""

import os
import sys
import json
import argparse
import datetime
import re
from pathlib import Path

WORKSPACE = Path(os.environ.get("CONTENT_MONITOR_WORKSPACE", str(Path.home() / ".openclaw" / "workspace")))
SITES_DIR = WORKSPACE / "sites"
DRAFTS_DIR = WORKSPACE / "posts" / "drafts"
STATE_FILE = WORKSPACE / "crawl-state.json"

FACEBOOK_TEMPLATE = """## Facebook Post

{facebook}

---

## X / Twitter Post

{twitter}

---

## Image Prompt (for Gemini / AI image generation)

{image_prompt}

---

## Source

- **URL:** {url}
- **Domain:** {domain}
- **Category:** {category}
- **Crawled at:** {crawled_at}
- **Draft created:** {draft_created}
"""


def parse_frontmatter(text):
    """Extract YAML-style frontmatter from markdown."""
    meta = {}
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            fm = text[3:end].strip()
            for line in fm.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
    return meta


def truncate_content(content, max_chars=3000):
    """Take first max_chars of the main content (after frontmatter), cleaned of markdown syntax."""
    # Remove frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            content = content[end + 3:].strip()
    # Strip image markdown first: ![alt](url) or ![alt](
    content = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', content)
    content = re.sub(r'!\[[^\]]*\]\(\s*$', '', content, flags=re.MULTILINE)
    # Strip markdown links: [text](url) → text
    content = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', content)
    # Strip bare URLs
    content = re.sub(r'https?://\S+', '', content)
    # Strip heading hashes
    content = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)
    # Strip cookie/privacy boilerplate lines
    noise_patterns = [
        r'.*cookie.*', r'.*privacy policy.*', r'.*personal data.*',
        r'.*do not sell.*', r'.*opt.out.*', r'.*third.party tools.*',
        r'.*skip to (content|main|navigation).*', r'.*javascript.*required.*',
    ]
    lines = content.splitlines()
    clean_lines = []
    for line in lines:
        low = line.lower()
        if any(re.search(p, low) for p in noise_patterns):
            continue
        clean_lines.append(line)
    content = '\n'.join(clean_lines)
    # Collapse multiple blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content.strip()[:max_chars]


def generate_draft_openai(content_excerpt, meta):
    """
    Generate draft using OpenAI-compatible API (if available).
    Falls back to template-based draft.
    """
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("GITHUB_COPILOT_TOKEN")
    if not api_key:
        return None
    # Not implemented here — agent should call LLM directly
    return None


def generate_draft_template(content_excerpt, meta):
    """Simple keyword-based draft. Agent should enhance using LLM."""
    domain = meta.get("domain", "unknown")
    category = meta.get("category", "general")
    url = meta.get("url", f"https://www.{domain}")

    # Extract first meaningful paragraph
    lines = [l.strip() for l in content_excerpt.splitlines() if len(l.strip()) > 60]
    first_para = lines[0] if lines else content_excerpt[:200]

    # Category-specific tone
    if "injury" in category or "personal-injury" in category:
        topic = "personal injury law"
        cta = "Know your rights. Free consultation available."
        hashtags = "#PersonalInjury #InjuryLaw #CaliforniaLaw #NevadaLaw #AccidentAttorney"
    else:
        topic = "home equity & mortgage solutions"
        cta = "Explore your home equity options today."
        hashtags = "#HomEquity #Mortgage #HomeEquityInvestment #RealEstate #HEI"

    facebook = (
        f"💡 Did you know? {first_para[:300]}\n\n"
        f"{cta}\n\n"
        f"Learn more → {url}\n\n"
        f"{hashtags}"
    )

    twitter = f"{first_para[:200]} {cta} {url}"[:280]

    image_prompt = (
        f"Professional, modern graphic for a {topic} social media post. "
        f"Clean design, trustworthy aesthetic, no text overlay. "
        f"Color palette: deep blue and white. Style: editorial/corporate."
    )

    return facebook, twitter, image_prompt


def process_file(filepath):
    path = Path(filepath)
    if not path.exists():
        print(f"  ERROR: File not found: {filepath}", file=sys.stderr)
        return

    text = path.read_text()
    meta = parse_frontmatter(text)
    content_excerpt = truncate_content(text)

    facebook, twitter, image_prompt = generate_draft_template(content_excerpt, meta)

    domain = meta.get("domain", path.stem)
    category = meta.get("category", "general")
    today = datetime.date.today().isoformat()

    out_dir = DRAFTS_DIR / category
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{domain}-{today}.md"

    draft = FACEBOOK_TEMPLATE.format(
        facebook=facebook,
        twitter=twitter,
        image_prompt=image_prompt,
        url=meta.get("url", ""),
        domain=domain,
        category=category,
        crawled_at=meta.get("crawled_at", ""),
        draft_created=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    out_file.write_text(draft)
    print(f"  Draft → {out_file.relative_to(WORKSPACE)}")


def process_all(category=None):
    search_dir = SITES_DIR / category if category else SITES_DIR
    files = list(search_dir.rglob("*.md"))
    if not files:
        print(f"No site files found in {search_dir}")
        return
    for f in files:
        process_file(f)


def main():
    parser = argparse.ArgumentParser(description="Generate social draft posts from crawled content")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Single .md site file to process")
    group.add_argument("--all", action="store_true", help="Process all site files")
    group.add_argument("--category", help="Process one category (personal-injury or mortgage)")
    args = parser.parse_args()

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.file:
        process_file(args.file)
    elif args.all:
        process_all()
    elif args.category:
        process_all(category=args.category)


if __name__ == "__main__":
    main()
