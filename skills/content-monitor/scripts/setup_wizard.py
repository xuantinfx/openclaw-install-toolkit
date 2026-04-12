#!/usr/bin/env python3
"""
setup_wizard.py — Utility functions for Content Monitor setup.

These functions are called by the agent during the setup wizard
(prompts/setup-wizard.md). They are NOT meant to be run interactively
by the user — the agent drives the setup conversation in chat.

Usage (by agent):
  python3 scripts/setup_wizard.py save-keys --firecrawl "fc-..." --google "AIzaSy..." [--brave "..."]
  python3 scripts/setup_wizard.py add-sites --category personal-injury --urls "site1.com,site2.com"
  python3 scripts/setup_wizard.py save-samples --text "sample post content here"
  python3 scripts/setup_wizard.py set-domain --domain "www.mysite.com"
  python3 scripts/setup_wizard.py init-workspace
  python3 scripts/setup_wizard.py status
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
WORKSPACE = Path.home() / ".openclaw" / "workspace"
ENV_FILE = WORKSPACE / ".env-content-monitor"
SITES_FILE = SKILL_DIR / "references" / "sites.md"
SAMPLE_POSTS_FILE = SKILL_DIR / "references" / "sample-posts.md"
WRITING_STYLE_FILE = SKILL_DIR / "references" / "writing-style.md"
CALENDAR_FILE = WORKSPACE / "content-calendar.json"
CRAWL_STATE_FILE = WORKSPACE / "crawl-state.json"


def cmd_save_keys(args):
    """Save API keys to .env file."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)

    # Load existing keys
    existing = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            match = re.match(r'export\s+(\w+)="([^"]*)"', line)
            if match:
                existing[match.group(1)] = match.group(2)

    # Update with new keys
    if args.firecrawl:
        existing["FIRECRAWL_API_KEY"] = args.firecrawl
    if args.google:
        existing["GOOGLE_AI_API_KEY"] = args.google
    if args.brave:
        existing["BRAVE_API_KEY"] = args.brave
    if args.google_search:
        existing["GOOGLE_SEARCH_API_KEY"] = args.google_search
    if args.google_cx:
        existing["GOOGLE_SEARCH_CX"] = args.google_cx

    lines = [
        "# Content Monitor API Keys",
        "# Source this file before running scripts:",
        "#   source ~/.openclaw/workspace/.env-content-monitor",
        "",
    ]
    for key, val in existing.items():
        if val:
            lines.append(f'export {key}="{val}"')

    ENV_FILE.write_text("\n".join(lines) + "\n")
    os.chmod(ENV_FILE, 0o600)
    print(f"API keys saved to {ENV_FILE}")


def cmd_add_sites(args):
    """Add websites to the monitored sites list."""
    urls = [u.strip() for u in args.urls.split(",") if u.strip()]
    if not urls:
        print("No URLs provided.", file=sys.stderr)
        return

    # Normalize URLs
    normalized = []
    for url in urls:
        url = url.strip().rstrip("/")
        if not url.startswith("http"):
            url = "https://" + url
        normalized.append(url)

    # Append to sites.md
    if not SITES_FILE.exists():
        content = "# Competitor Sites\n\n"
    else:
        content = SITES_FILE.read_text()

    category = args.category or "other"
    header = f"\n## {category.replace('-', ' ').title()} (Added by Setup Wizard)\n\n"
    site_lines = "\n".join(f"- {s}" for s in normalized)
    content += header + site_lines + "\n"

    SITES_FILE.write_text(content)
    print(f"Added {len(normalized)} sites to {category}.")


def cmd_save_samples(args):
    """Save sample post text and generate writing style guide."""
    text = args.text
    if not text:
        print("No sample text provided.", file=sys.stderr)
        return

    # Load existing samples
    samples = []
    if SAMPLE_POSTS_FILE.exists():
        existing = SAMPLE_POSTS_FILE.read_text()
        # Extract existing samples
        for match in re.finditer(r'```\n(.*?)\n```', existing, re.DOTALL):
            samples.append(match.group(1))

    samples.append(text)

    # Write sample-posts.md
    lines = ["# Sample Posts — Writing Style Reference\n"]
    lines.append("## User-Provided Samples\n")
    for i, sample in enumerate(samples, 1):
        lines.append(f"### Sample {i}\n")
        lines.append("```")
        lines.append(sample)
        lines.append("```\n")
    lines.append("## Default Sample (from themes.md)\n")
    lines.append("See themes.md for the default style examples.\n")
    SAMPLE_POSTS_FILE.write_text("\n".join(lines))

    # Generate writing style
    _generate_writing_style(samples)
    print(f"Saved {len(samples)} sample(s). Writing style guide updated.")


def _generate_writing_style(samples):
    """Analyze samples and generate a writing style guide."""
    all_text = "\n\n".join(samples)
    word_count = len(all_text.split())
    avg_words = word_count // len(samples) if samples else 0
    sentence_count = len(re.split(r'[.!?]+', all_text))
    avg_sentence_len = word_count // max(sentence_count, 1)

    has_emoji = bool(re.search(r'[\U0001F600-\U0001F9FF\U00002600-\U000027BF]', all_text))
    has_hashtags = bool(re.search(r'#\w+', all_text))
    has_questions = bool(re.search(r'\?', all_text))

    casual_words = len(re.findall(r"\b(you're|don't|can't|won't|here's|it's|that's)\b", all_text.lower()))
    formal_words = len(re.findall(r'\b(therefore|consequently|furthermore|moreover|pursuant)\b', all_text.lower()))
    tone = "casual and conversational" if casual_words > formal_words else "professional but approachable"

    lines = [
        "# Writing Style Guide\n",
        f"Auto-generated from {len(samples)} user-provided sample post(s).\n",
        "Scripts like `social_draft.py` read this file to match your writing tone.\n",
        "---\n",
        f"## Tone\n\n{tone.capitalize()}.",
    ]
    if has_questions:
        lines.append(" Uses rhetorical questions to engage the reader.")
    lines.append("\n")

    lines.append(f"## Length\n\n- Average post length: ~{avg_words} words")
    lines.append(f"- Average sentence length: ~{avg_sentence_len} words\n")

    lines.append("## Structure Patterns\n")
    if has_questions:
        lines.append("- Uses questions to open or engage")
    if avg_sentence_len < 15:
        lines.append("- Short, punchy sentences")
    else:
        lines.append("- Mix of short and longer explanatory sentences")
    lines.append("")

    lines.append("## Emoji Usage\n")
    if has_emoji:
        lines.append("- Emoji detected in samples — used sparingly\n")
    else:
        lines.append("- No emoji in samples — keep posts emoji-free or minimal\n")

    lines.append("## Hashtag Style\n")
    if has_hashtags:
        hashtags = re.findall(r'#\w+', all_text)
        lines.append(f"- {len(hashtags)} hashtags found across samples")
    else:
        lines.append("- No hashtags in samples — add 2-3 relevant hashtags at end")
    lines.append("")

    lines.append("## Do's\n")
    lines.append("- Match the tone and length observed in the samples above")
    lines.append("- Use specific facts, numbers, and real-world scenarios")
    lines.append("- Vary post structure (story, stat, question, myth, news angle, direct)\n")

    lines.append("## Don'ts\n")
    lines.append("- Don't use emoji as bullet points")
    lines.append("- Don't include links or URLs")
    lines.append("- Don't use generic filler phrases or CTAs")
    lines.append("- Don't repeat the same structure every day\n")

    lines.append("---\n")
    lines.append("_Read `references/sample-posts.md` for the actual sample texts._\n")

    WRITING_STYLE_FILE.write_text("\n".join(lines))


def cmd_set_domain(args):
    """Update domain in scripts."""
    domain = args.domain
    scripts = [
        SKILL_DIR / "scripts" / "suggest_daily.py",
        SKILL_DIR / "scripts" / "blog_draft.py",
    ]
    for script in scripts:
        if script.exists():
            content = script.read_text()
            content = content.replace("www.yoursite.com", domain)
            script.write_text(content)
    print(f"Domain set to: {domain}")


def cmd_init_workspace(args):
    """Create workspace directory structure and initialize data files."""
    dirs = [
        WORKSPACE / "sites" / "personal-injury",
        WORKSPACE / "sites" / "mortgage",
        WORKSPACE / "news",
        WORKSPACE / "posts" / "drafts" / "personal-injury",
        WORKSPACE / "posts" / "drafts" / "mortgage",
        WORKSPACE / "posts" / "drafts" / "general",
        WORKSPACE / "posts" / "images",
        WORKSPACE / "posts" / "approved",
        WORKSPACE / "posts" / "published",
        WORKSPACE / "memory",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    if not CALENDAR_FILE.exists():
        CALENDAR_FILE.write_text('{"posts": []}')
    if not CRAWL_STATE_FILE.exists():
        CRAWL_STATE_FILE.write_text('{"last_crawled": {}}')

    print("Workspace initialized.")


def cmd_save_themes(args):
    """Save custom weekly theme schedule."""
    schedule_file = SKILL_DIR / "references" / "theme-schedule.json"

    # Load existing or default
    if schedule_file.exists():
        data = json.loads(schedule_file.read_text())
    else:
        data = {
            "_comment": "Weekly theme rotation. Day 0=Monday, 6=Sunday.",
            "schedule": {},
            "available_themes": [
                "know_your_rights", "hei_education", "case_story",
                "market_news", "faq", "tips", "industry_news"
            ],
            "available_categories": ["personal-injury", "mortgage", "both"],
        }

    # Parse input: expects JSON string like {"0": {"category": "...", "theme": "..."}, ...}
    try:
        updates = json.loads(args.schedule)
    except json.JSONDecodeError:
        print("ERROR: --schedule must be valid JSON.", file=sys.stderr)
        sys.exit(1)

    day_labels = {
        "0": "Monday", "1": "Tuesday", "2": "Wednesday",
        "3": "Thursday", "4": "Friday", "5": "Saturday", "6": "Sunday"
    }

    for day_str, config in updates.items():
        config["label"] = day_labels.get(day_str, f"Day {day_str}")
        data["schedule"][day_str] = config

    schedule_file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    # Print summary
    for day_str in sorted(data["schedule"].keys()):
        entry = data["schedule"][day_str]
        print(f"  {entry.get('label', day_str):12s} → {entry['category']:20s} | {entry['theme']}")


def cmd_status(args):
    """Show current setup status."""
    status = {}

    # API keys
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            match = re.match(r'export\s+(\w+)="([^"]*)"', line)
            if match and match.group(2):
                status[match.group(1)] = f"{match.group(2)[:8]}..."

    # Sites count
    if SITES_FILE.exists():
        urls = re.findall(r'https?://[^\s\)]+', SITES_FILE.read_text())
        status["sites_count"] = len(urls)

    # Samples
    if SAMPLE_POSTS_FILE.exists():
        content = SAMPLE_POSTS_FILE.read_text()
        samples = re.findall(r'```\n', content)
        status["samples_count"] = len(samples)

    # Writing style
    status["writing_style"] = "custom" if WRITING_STYLE_FILE.exists() and "Auto-generated from" in WRITING_STYLE_FILE.read_text() else "default"

    # Workspace
    status["workspace_ready"] = CALENDAR_FILE.exists()

    print(json.dumps(status, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Content Monitor setup utilities (used by agent)")
    sub = parser.add_subparsers(dest="command")

    # save-keys
    p = sub.add_parser("save-keys", help="Save API keys")
    p.add_argument("--firecrawl", default="")
    p.add_argument("--google", default="")
    p.add_argument("--brave", default="")
    p.add_argument("--google-search", default="")
    p.add_argument("--google-cx", default="")

    # add-sites
    p = sub.add_parser("add-sites", help="Add monitored websites")
    p.add_argument("--category", default="other")
    p.add_argument("--urls", required=True, help="Comma-separated URLs")

    # save-samples
    p = sub.add_parser("save-samples", help="Save sample post text")
    p.add_argument("--text", required=True, help="Sample post text")

    # save-themes
    p = sub.add_parser("save-themes", help="Save custom weekly theme schedule")
    p.add_argument("--schedule", required=True, help='JSON: {"0": {"category": "...", "theme": "..."}, ...}')

    # set-domain
    p = sub.add_parser("set-domain", help="Set website domain")
    p.add_argument("--domain", required=True)

    # init-workspace
    sub.add_parser("init-workspace", help="Create workspace directories")

    # status
    sub.add_parser("status", help="Show setup status")

    args = parser.parse_args()

    commands = {
        "save-keys": cmd_save_keys,
        "add-sites": cmd_add_sites,
        "save-samples": cmd_save_samples,
        "save-themes": cmd_save_themes,
        "set-domain": cmd_set_domain,
        "init-workspace": cmd_init_workspace,
        "status": cmd_status,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
