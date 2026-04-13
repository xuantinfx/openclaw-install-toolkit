#!/usr/bin/env python3
"""
social_draft.py - Generate content briefs for the agent to write social posts.

This script does NOT write final post text. It assembles context (topic, news,
competitor data, guidelines) into a structured brief. The OpenClaw agent reads
the brief and writes the actual Facebook + X posts.

Usage:
  python3 social_draft.py --from-calendar
  python3 social_draft.py --from-calendar --date 2026-04-10
  python3 social_draft.py --topic "What to do after a car accident" --category personal-injury

Output:
  posts/drafts/<timestamp>/<slug>.md (content brief for agent)
"""

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
SKILL_DIR = Path(__file__).parent.parent
DRAFTS_DIR = WORKSPACE / "posts" / "drafts"
SITES_DIR = WORKSPACE / "sites"
NEWS_DIR = WORKSPACE / "news"
CALENDAR_FILE = WORKSPACE / "content-calendar.json"
WRITING_STYLE_FILE = SKILL_DIR / "references" / "writing-style.md"
SAMPLE_POSTS_FILE = SKILL_DIR / "references" / "sample-posts.md"

# Hashtags — fewer, more targeted, rotated
PI_HASHTAGS = [
    ["#PersonalInjury", "#CaliforniaLaw", "#KnowYourRights"],
    ["#InjuryLaw", "#AccidentClaim", "#LegalTips"],
    ["#CarAccident", "#InjuryAttorney", "#NevadaLaw"],
]

MORT_HASHTAGS = [
    ["#HomeEquity", "#RealEstate", "#Homeowner"],
    ["#MortgageTips", "#HEI", "#HomeFinance"],
    ["#EquityUnlocked", "#SmartHomeowner", "#CaliforniaRealEstate"],
]

STRUCTURE_DESCRIPTIONS = {
    "story": "**Story opener** — start with a relatable real-world scenario that the reader can picture themselves in, then transition into the topic with insight.",
    "stat": "**Stat hook** — lead with a surprising, specific number or data point, then explain what it means for the reader.",
    "question": "**Question lead** — open with a provocative question the reader hasn't considered, then provide a substantive answer.",
    "myth": "**Myth buster** — state a common misconception in quotes, then dismantle it with facts and nuance.",
    "news_angle": "**News angle** — reference the recent headline from News Context below, then connect it to practical advice for the reader.",
    "direct": "**Direct value** — skip framing, go straight to the actionable insight. Lead with the most useful piece of information.",
}


def slug_from_title(title):
    t = title.lower()
    t = re.sub(r'[^a-z0-9\s-]', '', t)
    t = re.sub(r'\s+', '-', t.strip())
    t = re.sub(r'-+', '-', t)
    return t[:80]


def pick_hashtags(category, date_str):
    seed = int(hashlib.md5(date_str.encode()).hexdigest(), 16)
    pool = PI_HASHTAGS if "injury" in category else MORT_HASHTAGS
    tags = pool[seed % len(pool)]
    return " ".join(tags)


def pick_structure(theme, date_str, has_news=False):
    structures = ["story", "stat", "question", "myth", "direct"]
    if has_news:
        structures.append("news_angle")
    seed = int(hashlib.md5(f"{date_str}-{theme}".encode()).hexdigest(), 16)
    return structures[seed % len(structures)]


# ---------------------------------------------------------------------------
# DATA GATHERING
# ---------------------------------------------------------------------------

def load_news_for_theme(theme, date_str):
    news_file = NEWS_DIR / f"{date_str}-{theme}.json"
    if news_file.exists():
        try:
            items = json.loads(news_file.read_text())
            return [i for i in items if i.get("title")][:3]
        except (json.JSONDecodeError, KeyError):
            pass
    return []


def load_competitor_snippets(category, topic_title=""):
    """Load competitor content relevant to the topic."""
    snippets = []

    # Source 1: structured topics from .topics/ JSON
    categories_to_scan = [category] if category not in ("general", "both") else ["personal-injury", "mortgage"]
    for cat in categories_to_scan:
        topics_dir = SITES_DIR / cat / ".topics"
        if topics_dir.exists():
            for f in topics_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    domain = data.get("domain", f.stem)
                    for t in data.get("topics", []):
                        # Find topics related to our topic
                        if topic_title and _topic_overlap(topic_title, t.get("title", "")):
                            snippets.append({"domain": domain, "title": t["title"], "type": t.get("type", "article")})
                except (json.JSONDecodeError, KeyError):
                    continue

    # Source 2: raw markdown sentences (fallback)
    if not snippets:
        for cat in categories_to_scan:
            cat_dir = SITES_DIR / cat
            if not cat_dir.exists():
                continue
            files = list(cat_dir.glob("*.md"))
            rng = random.Random(datetime.date.today().isoformat())
            rng.shuffle(files)
            for f in files[:5]:
                text = f.read_text(errors="ignore")
                if text.startswith("---"):
                    end = text.find("---", 3)
                    if end > 0:
                        text = text[end + 3:].strip()
                text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
                text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
                text = re.sub(r'https?://\S+', '', text)
                text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
                sentences = re.split(r'[.!?]\s+', text)
                useful = [s.strip() for s in sentences if 50 < len(s.strip()) < 250]
                if useful:
                    snippets.append({"domain": f.stem, "content": useful[0]})

    return snippets[:8]


def _topic_overlap(topic_a, topic_b):
    """Check if two topics share significant keywords."""
    words_a = set(re.findall(r'\w{4,}', topic_a.lower()))
    words_b = set(re.findall(r'\w{4,}', topic_b.lower()))
    if not words_a or not words_b:
        return False
    overlap = words_a & words_b
    return len(overlap) >= 2


def generate_key_points(title, category, theme):
    """Generate suggested key points based on topic and theme."""
    clean = title.lower()
    points = []

    # Theme-based key points
    if theme == "know_your_rights":
        points = [
            "What specific rights apply in this situation",
            "Common mistakes that waive or weaken these rights",
            "Time limits or deadlines the reader should know",
            "What to do first (immediate actionable step)",
            "When professional help is necessary vs. handling it alone",
        ]
    elif theme == "hei_education":
        points = [
            "How this specific aspect of HEI works mechanically",
            "Real numbers: typical percentages, terms, or costs involved",
            "How it compares to the traditional alternative (HELOC, refi)",
            "Who benefits most from this (and who should avoid it)",
            "One thing most people get wrong about this topic",
        ]
    elif theme == "case_story":
        points = [
            "What makes this type of case different from typical accidents",
            "Who is liable and why (specific legal basis)",
            "What compensation is typically available",
            "A common pitfall that reduces or eliminates the claim",
            "The timeline from incident to resolution",
        ]
    elif theme == "market_news":
        points = [
            "What changed and why it matters to homeowners specifically",
            "Concrete impact: how this affects monthly payments, equity, or options",
            "What to do now vs. wait (actionable timing advice)",
            "How this compares to the situation 6-12 months ago",
        ]
    elif theme == "faq":
        points = [
            "The direct, honest answer (not a hedge)",
            "The most important factor that determines the answer",
            "A specific example or scenario that illustrates the answer",
            "What most people assume (incorrectly) about this",
            "One thing to do right now based on this information",
        ]
    elif theme == "tips":
        points = [
            "The single most impactful tip (lead with this)",
            "A specific number, threshold, or benchmark to reference",
            "A mistake that costs real money if ignored",
            "How to verify or compare (what to look for)",
            "The one question to ask before signing anything",
        ]
    elif theme == "industry_news":
        points = [
            "What is changing and who decided it",
            "How this directly affects the reader's situation",
            "What to do differently as a result",
            "Timeline: when does this take effect",
        ]
    else:
        points = [
            "The core insight the reader should walk away with",
            "A specific fact, number, or example that supports it",
            "What most people misunderstand about this topic",
            "One concrete action the reader can take",
        ]

    return points


# ---------------------------------------------------------------------------
# WRITING STYLE
# ---------------------------------------------------------------------------

def load_writing_style():
    """Load custom writing style guide if available."""
    if WRITING_STYLE_FILE.exists():
        content = WRITING_STYLE_FILE.read_text().strip()
        # Skip if it's just the default template with no customization
        if "_This file was generated with default style guidelines_" in content:
            return ""
        return content
    return ""


def load_sample_posts():
    """Load sample posts for reference in briefs."""
    if SAMPLE_POSTS_FILE.exists():
        content = SAMPLE_POSTS_FILE.read_text().strip()
        if "No samples provided yet" in content:
            return ""
        # Extract just the user-provided samples section
        if "## User-Provided Samples" in content:
            start = content.index("## User-Provided Samples")
            end = content.index("## Default Sample") if "## Default Sample" in content else len(content)
            section = content[start:end].strip()
            if "```" in section:  # Has actual sample content
                return section
    return ""


# ---------------------------------------------------------------------------
# CONTENT BRIEF BUILDER
# ---------------------------------------------------------------------------

def build_content_brief(title, category, theme, news_refs, snippets, date_str, source_type=""):
    """Build a structured content brief for the agent to write from."""
    clean_title = title.replace("FAQ: ", "").strip()
    has_news = len(news_refs) > 0
    structure = pick_structure(theme, date_str, has_news=has_news)
    structure_desc = STRUCTURE_DESCRIPTIONS.get(structure, STRUCTURE_DESCRIPTIONS["direct"])
    hashtags = pick_hashtags(category, date_str)
    key_points = generate_key_points(title, category, theme)

    lines = []
    lines.append("# Content Brief\n")

    # Topic
    lines.append("## Topic")
    lines.append(f"{clean_title}\n")

    # Structure
    lines.append("## Structure")
    lines.append(f"{structure_desc}\n")

    # News context
    lines.append("## News Context")
    if news_refs:
        for n in news_refs:
            source = n.get("source", "unknown")
            published = n.get("published", "")
            snippet = n.get("snippet", "")
            lines.append(f"- \"{n['title']}\" ({source}, {published})")
            if snippet:
                lines.append(f"  {snippet}")
    else:
        lines.append("No recent news available for this theme today.")
    lines.append("")

    # Competitor angles
    lines.append("## Competitor Angles")
    if snippets:
        for s in snippets:
            domain = s.get("domain", "unknown")
            if "title" in s:
                lines.append(f"- {domain}: \"{s['title']}\"")
            elif "content" in s:
                lines.append(f"- {domain}: \"{s['content']}\"")
    else:
        lines.append("No competitor content available for this topic.")
    lines.append("")

    # Key points
    lines.append("## Key Points to Cover")
    for p in key_points:
        lines.append(f"- {p}")
    lines.append("")

    # Writing guidelines
    lines.append("## Writing Guidelines")
    lines.append("- No links or URLs anywhere in the post")
    lines.append("- No emoji as bullet points or structural elements (no checkmarks, arrows, warning signs)")
    lines.append("- Max 1 emoji at the very start of Facebook post (optional, skip if unnatural)")
    lines.append("- Facebook: max 400 words, must teach the reader something specific")
    lines.append("- X/Twitter: max 280 characters, one sharp insight")
    lines.append("- Use specific facts, numbers, jurisdictions, or timeframes — not generic advice")
    lines.append("- Acknowledge nuance where it exists (\"it depends\", \"in most cases\", \"terms vary\")")
    lines.append("- Write for someone who has never thought about this topic before")
    lines.append("- The reader should finish the post knowing something they didn't before")
    lines.append("- Do NOT use filler phrases: \"Here's what you need to know\", \"Stay informed\", \"Knowledge is power\"")
    lines.append("- Do NOT end with generic CTAs: \"Don't navigate this alone\", \"Protect your rights\"")
    lines.append("")

    # Hashtags
    lines.append("## Hashtags")
    lines.append(f"{hashtags}\n")

    # Writing style reference (from setup wizard samples)
    style = load_writing_style()
    samples = load_sample_posts()
    if style or samples:
        lines.append("## Writing Style Reference")
        lines.append("Match this style when writing the posts:\n")
        if style:
            # Extract just the key sections (Tone, Do's, Don'ts)
            for section in ["## Tone", "## Do's", "## Don'ts"]:
                if section in style:
                    start = style.index(section)
                    # Find next section
                    next_section = style.find("\n## ", start + len(section))
                    end = next_section if next_section > 0 else len(style)
                    lines.append(style[start:end].strip())
                    lines.append("")
        if samples:
            lines.append("### Reference Samples")
            lines.append(samples)
            lines.append("")

    return "\n".join(lines), structure


def build_image_prompt(title, category, theme):
    if "injury" in category or "personal" in category:
        style_map = {
            "faq":              "Professional attorney in a modern office consulting with a client across a desk, warm lighting, eye-level shot",
            "know_your_rights": "Confident person standing in front of a courthouse, golden hour, wide shot, empowering mood",
            "case_story":       "Cinematic wide shot of a busy intersection at dusk, emergency lights in background, editorial photography",
            "industry_news":    "Modern law office boardroom with city skyline through floor-to-ceiling windows, professionals in discussion",
        }
        style = style_map.get(theme, "Professional legal environment, warm office lighting")
        return (
            f"Photorealistic editorial photograph. {style}. "
            f"No text, no logos, no watermarks. "
            f"Color palette: deep blue, warm wood tones, natural light. "
            f"Shot on medium format camera, shallow depth of field. 1080x1080 square crop."
        )
    else:
        style_map = {
            "hei_education":  "Happy homeowner couple standing in front of their suburban home, golden hour, warm tones, mid-shot",
            "tips":           "Homeowner reviewing financial documents at kitchen table with laptop, natural morning light",
            "market_news":    "Aerial view of a beautiful suburban neighborhood, warm afternoon light, real estate photography",
            "industry_news":  "Modern financial district with residential homes in foreground, blending urban and suburban, editorial",
        }
        style = style_map.get(theme, "Beautiful suburban home exterior, warm natural light")
        return (
            f"Photorealistic editorial photograph. {style}. "
            f"No text, no logos, no watermarks. "
            f"Color palette: warm earth tones, green landscaping, blue sky. "
            f"Shot on medium format camera, natural depth of field. 1080x1080 square crop."
        )


# ---------------------------------------------------------------------------
# DRAFT GENERATION
# ---------------------------------------------------------------------------

DRAFT_TEMPLATE = """\
---
title: {title}
category: {category}
theme: {theme}
date: {date}
source_type: {source_type}
structure: {structure}
status: brief
---

{content_brief}

---

# Facebook Post

[AGENT: Write the Facebook post here using the Content Brief above. Make it specific to the topic, reference facts from News Context and Competitor Angles, and follow the Writing Guidelines exactly.]

---

# X / Twitter Post

[AGENT: Write the X post here. Max 280 characters. One sharp, specific insight from the topic. Use hashtags from the brief.]

---

# Image Prompt (Gemini / AI image generator)

{image_prompt}

---

# Review Checklist

- [ ] Agent wrote Facebook + X posts from the brief
- [ ] Posts are specific to the topic (not generic template text)
- [ ] Posts reference real facts from news or competitor data
- [ ] No emoji bullets, no generic CTAs, no filler phrases
- [ ] Facebook: max 400 words, max 3 hashtags
- [ ] X: max 280 chars, max 2 hashtags
- [ ] Generate image using prompt above
- [ ] User reviewed and approved
"""


def generate_draft(title, category, theme, date_str=None, source_type=""):
    date_str = date_str or datetime.date.today().isoformat()
    slug = slug_from_title(title)

    news_refs = load_news_for_theme(theme, date_str)
    snippets = load_competitor_snippets(category, topic_title=title)

    content_brief, structure = build_content_brief(
        title, category, theme, news_refs, snippets, date_str, source_type
    )
    image_prompt = build_image_prompt(title, category, theme)

    draft = DRAFT_TEMPLATE.format(
        title=title,
        category=category,
        theme=theme,
        date=date_str,
        source_type=source_type or "manual",
        structure=structure,
        content_brief=content_brief,
        image_prompt=image_prompt,
    )

    out_dir = DRAFTS_DIR / datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{slug}.md"
    out_file.write_text(draft)
    print(f"  Brief -> {out_file.relative_to(WORKSPACE)}")
    return out_file


def from_calendar(date_str=None):
    if not CALENDAR_FILE.exists():
        print("ERROR: content-calendar.json not found. Run suggest_daily.py --record first.", file=sys.stderr)
        sys.exit(1)
    cal = json.loads(CALENDAR_FILE.read_text())
    date_str = date_str or datetime.date.today().isoformat()
    todays = [p for p in cal.get("posts", []) if p.get("date") == date_str]
    if not todays:
        print(f"No suggestions for {date_str}. Run suggest_daily.py --record first.")
        return
    for s in todays:
        generate_draft(
            title=s["title"],
            category=s["category"],
            theme=s["theme"],
            date_str=date_str,
            source_type=s.get("source_type", ""),
        )


def main():
    parser = argparse.ArgumentParser(description="Generate content briefs for Facebook + X posts")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--topic", help="Topic/title to write about")
    group.add_argument("--from-calendar", action="store_true", help="Use today's calendar suggestions")
    parser.add_argument("--category", default="personal-injury",
                        choices=["personal-injury", "mortgage", "general"])
    parser.add_argument("--theme", default="know_your_rights")
    parser.add_argument("--date", help="Date override (YYYY-MM-DD)")
    args = parser.parse_args()

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.from_calendar:
        from_calendar(args.date)
    else:
        generate_draft(args.topic, args.category, args.theme, args.date)


if __name__ == "__main__":
    main()
