#!/usr/bin/env python3
"""
approve_post.py - Approve a draft and optionally auto-post to Facebook + X.

Structure:
  posts/drafts/YYYY-MM-DD-HHMM/
    ├── slug.md
    └── slug.jpg

  posts/approved/YYYY-MM-DD-HHMM/
    ├── slug.md
    └── slug.jpg

Usage:
  python3 approve_post.py --draft posts/drafts/2026-04-06-2053/my-post.md
  python3 approve_post.py --draft posts/drafts/2026-04-06-2053/my-post.md --auto-post
  python3 approve_post.py --draft posts/drafts/2026-04-06-2053/my-post.md --auto-post --dry-run
  python3 approve_post.py --publish posts/approved/2026-04-06-2053
"""

import sys
import argparse
import datetime
import shutil
import subprocess
from pathlib import Path

WORKSPACE     = Path(__file__).parent.parent.parent.parent
DRAFTS_DIR    = WORKSPACE / "posts" / "drafts"
APPROVED_DIR  = WORKSPACE / "posts" / "approved"
PUBLISHED_DIR = WORKSPACE / "posts" / "published"
AUTO_POST_SCRIPT = Path(__file__).parent / "auto_post.py"


def approve(draft_path_str, auto_post=False, dry_run=False):
    draft = Path(draft_path_str)
    if not draft.exists():
        draft = WORKSPACE / draft_path_str
    if not draft.exists():
        print(f"ERROR: Not found: {draft_path_str}", file=sys.stderr)
        sys.exit(1)

    # Draft folder: posts/drafts/YYYY-MM-DD-HHMM/
    draft_folder = draft.parent
    now = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    dest = APPROVED_DIR / now
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)

    shutil.copytree(str(draft_folder), str(dest))
    shutil.rmtree(str(draft_folder))

    # Find the .md file in approved folder
    md_files = list(dest.glob("*.md"))
    approved_draft = md_files[0] if md_files else None

    print(f"\nApproved -> posts/approved/{now}/")
    for f in sorted(dest.iterdir()):
        if f.is_file():
            print(f"   - {f.name}")

    # Auto-post if requested
    if auto_post and approved_draft:
        print(f"\nGenerating auto-post instructions...")
        cmd = [sys.executable, str(AUTO_POST_SCRIPT), "--draft", str(approved_draft)]
        if dry_run:
            cmd.append("--dry-run")

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            # Save instructions for the agent to execute
            instructions_file = dest / "AUTO-POST-INSTRUCTIONS.md"
            instructions_file.write_text(result.stdout, encoding="utf-8")
            print(f"\nAuto-post instructions saved to: {instructions_file.name}")
            print("Agent: read this file and execute the browser steps via CDP relay.")
            # Also print to stdout so the agent sees it directly
            print("\n" + result.stdout)
        return dest

    if not auto_post:
        print(f"\nTo auto-post:")
        print(f"   python3 auto_post.py --draft {approved_draft}")
        print(f"\nOr post manually, then run:")
        print(f"   python3 approve_post.py --publish posts/approved/{now}")

    return dest


def publish(folder_path_str):
    folder = Path(folder_path_str)
    if not folder.exists():
        folder = WORKSPACE / folder_path_str
    if not folder.exists():
        print(f"ERROR: Not found: {folder}", file=sys.stderr)
        sys.exit(1)

    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
    dest = PUBLISHED_DIR / folder.name
    shutil.move(str(folder), str(dest))

    print(f"\nPublished -> posts/published/{folder.name}/")
    for f in sorted(dest.iterdir()):
        if f.is_file():
            print(f"   - {f.name}")


def main():
    parser = argparse.ArgumentParser(description="Approve, auto-post, or publish a post")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--draft", help="Path to any .md file inside the draft folder")
    group.add_argument("--publish", help="Path to approved folder to mark as published")
    parser.add_argument("--auto-post", action="store_true",
                        help="Automatically post to Facebook + X after approving")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fill posts but do NOT click publish (preview only)")
    args = parser.parse_args()

    if args.draft:
        approve(args.draft, auto_post=args.auto_post, dry_run=args.dry_run)
    elif args.publish:
        publish(args.publish)


if __name__ == "__main__":
    main()
