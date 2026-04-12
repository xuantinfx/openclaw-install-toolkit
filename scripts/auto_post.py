#!/usr/bin/env python3
"""
auto_post.py - Post approved content to Facebook and X via OpenClaw browser relay.

Uses the built-in Chrome browser relay (CDP protocol via gateway) — the same Chrome
profile where you're already logged in to Facebook and X.

No extra dependencies. No Playwright. No separate browser install.

Prerequisites:
  - OpenClaw gateway running (port 18789)
  - Chrome extension "Clawdbot Browser Relay" installed and active
  - Facebook and X already logged in within the OpenClaw Chrome profile

Usage:
  # Post an approved draft to both platforms
  python3 auto_post.py --draft posts/approved/2026-04-08-0700/slug.md

  # Post to Facebook only
  python3 auto_post.py --draft posts/approved/2026-04-08-0700/slug.md --facebook-only

  # Post to X only
  python3 auto_post.py --draft posts/approved/2026-04-08-0700/slug.md --x-only

  # Dry run: navigate and fill content, but do NOT click publish
  python3 auto_post.py --draft posts/approved/2026-04-08-0700/slug.md --dry-run

Note:
  This script prepares the content and instructs the OpenClaw agent to execute
  browser actions via the gateway. It can also be called by the agent directly
  using the browser CDP relay tools.
"""

import argparse
import base64
import json
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent.parent.parent


def parse_draft(draft_path: Path) -> dict:
    """Parse a draft markdown file into structured content."""
    content = draft_path.read_text(encoding="utf-8")

    # Extract frontmatter
    meta = {}
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            for line in content[3:end].strip().split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    meta[key.strip()] = val.strip()
            content = content[end + 3:]

    # Extract sections
    sections = {}
    current_section = None
    current_lines = []

    for line in content.split("\n"):
        header = re.match(r"^#\s+(.+)", line)
        if header:
            if current_section:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = header.group(1).strip()
            current_lines = []
        elif line.strip() == "---":
            if current_section:
                sections[current_section] = "\n".join(current_lines).strip()
                current_section = None
                current_lines = []
        else:
            current_lines.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_lines).strip()

    # Find image file
    image_path = find_image(draft_path)

    return {
        "title": meta.get("title", ""),
        "category": meta.get("category", ""),
        "theme": meta.get("theme", ""),
        "facebook": sections.get("Facebook Post", ""),
        "twitter": sections.get("X / Twitter Post", ""),
        "image_path": image_path,
    }


def find_image(draft_path: Path):
    """Find the image file associated with a draft."""
    draft_dir = draft_path.parent

    # Check same directory
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        images = list(draft_dir.glob(ext))
        if images:
            return images[0]

    # Check images dir by category + slug
    slug = draft_path.stem
    for cat_dir in (WORKSPACE / "posts" / "images").glob("*"):
        if cat_dir.is_dir():
            for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
                for img in cat_dir.glob(ext):
                    if slug in img.stem:
                        return img

    return None


def generate_agent_instructions(draft: dict, dry_run: bool = False,
                                 facebook: bool = True, x: bool = True) -> str:
    """Generate step-by-step instructions for the OpenClaw agent to execute via browser relay."""

    instructions = []
    instructions.append("# Auto-Post Instructions")
    instructions.append("")
    instructions.append(f"**Title**: {draft['title']}")
    instructions.append(f"**Image**: {draft['image_path'] or 'none'}")
    instructions.append(f"**Mode**: {'DRY RUN (do NOT click publish)' if dry_run else 'LIVE — will publish'}")
    instructions.append("")

    if facebook and draft["facebook"]:
        instructions.append("## Step 1: Post to Facebook")
        instructions.append("")
        instructions.append("1. Open a new browser tab and navigate to `https://www.facebook.com/`")
        instructions.append("2. Wait for the page to fully load (you should be logged in)")
        instructions.append("3. Click the \"What's on your mind?\" composer area to open the post editor")
        instructions.append("4. Wait for the post editor modal/dialog to appear")
        instructions.append("5. Click the text input area inside the post editor")
        instructions.append("6. Type the following Facebook post content:")
        instructions.append("")
        instructions.append("```")
        instructions.append(draft["facebook"])
        instructions.append("```")
        instructions.append("")

        if draft["image_path"]:
            instructions.append(f"7. Click the \"Photo/video\" button in the post editor")
            instructions.append(f"8. Upload the image file: `{draft['image_path']}`")
            instructions.append(f"9. Wait for the image upload to complete")

        if dry_run:
            instructions.append("")
            instructions.append("**STOP HERE — DO NOT CLICK POST. This is a dry run.**")
            instructions.append("Verify the content looks correct, then close the tab.")
        else:
            instructions.append("10. Click the \"Post\" button to publish")
            instructions.append("11. Wait 3-5 seconds for the post to be published")
            instructions.append("12. Verify the post appears in the feed")

        instructions.append("")

    if x and draft["twitter"]:
        step_offset = 1 if not facebook else 2
        instructions.append(f"## Step {step_offset}: Post to X (Twitter)")
        instructions.append("")
        instructions.append("1. Open a new browser tab and navigate to `https://x.com/compose/post`")
        instructions.append("2. Wait for the compose dialog to appear (you should be logged in)")
        instructions.append("3. Click the tweet text area")
        instructions.append("4. Type the following X post content:")
        instructions.append("")
        instructions.append("```")
        instructions.append(draft["twitter"])
        instructions.append("```")
        instructions.append("")

        if draft["image_path"]:
            img = draft['image_path']
            instructions.append("5. To upload an image to X, use this workaround (X uses a React-controlled hidden file input):")
            instructions.append("   a. Run: openclaw browser evaluate 'document.querySelector(\"input[data-testid=\\\"fileInput\\\"]\").click()'")
            instructions.append("      This triggers the native file chooser via the hidden input.")
            instructions.append(f"   b. Immediately run: openclaw browser upload {img}")
            instructions.append("      This intercepts the file chooser and selects the image.")
            instructions.append("7. Wait for the image upload to complete")

        if dry_run:
            instructions.append("")
            instructions.append("**STOP HERE — DO NOT CLICK POST. This is a dry run.**")
            instructions.append("Verify the content looks correct, then close the tab.")
        else:
            instructions.append("8. Click the \"Post\" button to publish")
            instructions.append("9. Wait 3-5 seconds for the post to appear")

    return "\n".join(instructions)


def main():
    parser = argparse.ArgumentParser(
        description="Generate browser instructions for auto-posting to Facebook and X")
    parser.add_argument("--draft", required=True, help="Path to approved draft markdown file")
    parser.add_argument("--facebook-only", action="store_true", help="Post to Facebook only")
    parser.add_argument("--x-only", action="store_true", help="Post to X only")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fill post content but do NOT click publish")
    parser.add_argument("--output", help="Save instructions to file instead of stdout")
    args = parser.parse_args()

    # Resolve draft path
    draft_path = Path(args.draft).resolve()
    if not draft_path.exists():
        draft_path = WORKSPACE / args.draft
    if not draft_path.exists():
        print(f"ERROR: Draft not found: {args.draft}", file=sys.stderr)
        sys.exit(1)

    # Parse draft
    draft = parse_draft(draft_path)
    if not draft["facebook"] and not draft["twitter"]:
        print("ERROR: No post content found in draft.", file=sys.stderr)
        sys.exit(1)

    # Determine platforms
    do_facebook = not args.x_only
    do_x = not args.facebook_only

    # Generate instructions
    instructions = generate_agent_instructions(
        draft,
        dry_run=args.dry_run,
        facebook=do_facebook,
        x=do_x,
    )

    if args.output:
        Path(args.output).write_text(instructions, encoding="utf-8")
        print(f"Instructions saved to: {args.output}", file=sys.stderr)
    else:
        print(instructions)


if __name__ == "__main__":
    main()
