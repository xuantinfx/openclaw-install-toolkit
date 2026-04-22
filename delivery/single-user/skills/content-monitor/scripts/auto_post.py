#!/usr/bin/env python3
"""
auto_post.py - Post approved content to Facebook and X via Playwright CDP.

Connects to a Chrome instance running with --remote-debugging-port=18800.
Uses Playwright's set_input_files() for image upload (no Finder dialog)
and JS evaluate() clicks to bypass overlay elements.

Prerequisites:
  - Chrome launched with CDP (run manually or use --start-chrome):
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \\
        --remote-debugging-port=18800 \\
        --user-data-dir="/tmp/chrome-openclaw-cdp" \\
        --no-first-run \\
        "https://www.facebook.com"
  - Facebook and X logged in within that Chrome session
  - playwright installed: pip install playwright && playwright install chromium

Usage:
  # Post an approved draft to both platforms
  python3 auto_post.py --draft posts/approved/2026-04-08-0700/slug.md

  # Post to Facebook only
  python3 auto_post.py --draft posts/approved/2026-04-08-0700/slug.md --facebook-only

  # Post to X only
  python3 auto_post.py --draft posts/approved/2026-04-08-0700/slug.md --x-only

  # Dry run: fill content but do NOT click publish
  python3 auto_post.py --draft posts/approved/2026-04-08-0700/slug.md --dry-run

  # Start Chrome CDP automatically, then post
  python3 auto_post.py --draft posts/approved/2026-04-08-0700/slug.md --start-chrome

Key techniques (see references/browser-autopost-working-method.md):
  1. set_input_files()   — inject image directly, no Finder dialog
  2. page.evaluate() JS — bypass overlay divs that block Playwright clicks
  3. Text-based JS search — find buttons by text content (stable vs class selectors)
"""

import os
import argparse
import asyncio
import base64
import json
import re
import subprocess
import sys
import time
from pathlib import Path

WORKSPACE = Path(os.environ.get("CONTENT_MONITOR_WORKSPACE", str(Path.home() / ".openclaw" / "workspace")))
CDP_PORT = 18800
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"
CHROME_USER_DATA = "/tmp/chrome-openclaw-cdp"


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


def is_cdp_ready() -> bool:
    """Check if Chrome CDP is reachable."""
    import urllib.request
    try:
        urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=3)
        return True
    except Exception:
        return False


def start_chrome_cdp() -> bool:
    """Launch Chrome with remote debugging. Returns True when CDP is ready."""
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not Path(chrome_path).exists():
        print("ERROR: Google Chrome not found.", file=sys.stderr)
        return False

    subprocess.run(["pkill", "-f", "chrome-openclaw-cdp"], capture_output=True)
    time.sleep(1)

    subprocess.Popen(
        [
            chrome_path,
            f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={CHROME_USER_DATA}",
            "--no-first-run",
            "--no-default-browser-check",
            "https://www.facebook.com",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(20):
        time.sleep(0.5)
        if is_cdp_ready():
            print("Chrome CDP ready.", file=sys.stderr)
            return True
    print("ERROR: Chrome CDP did not become ready.", file=sys.stderr)
    return False


async def _post_facebook(context, post_text: str, image_path, dry_run: bool) -> bool:
    """Post to Facebook via Playwright CDP."""
    fb_page = None
    for page in context.pages:
        if "facebook.com" in page.url and "fbsbx" not in page.url and "sw?" not in page.url:
            fb_page = page
            break

    if not fb_page:
        fb_page = await context.new_page()
        await fb_page.goto("https://www.facebook.com")
        await fb_page.wait_for_load_state("networkidle", timeout=15000)

    await fb_page.bring_to_front()
    await asyncio.sleep(2)

    if "login" in fb_page.url:
        print("[Facebook] Not logged in!", file=sys.stderr)
        return False

    # Open composer via JS text search (stable across FB UI changes)
    result = await fb_page.evaluate("""
        () => {
            const spans = Array.from(document.querySelectorAll('span'));
            for (const s of spans) {
                const t = s.textContent.trim();
                if (t.includes('\u0111ang ngh\u0129') || t.includes("What's on your mind") || t.includes('on your mind')) {
                    const btn = s.closest('[role="button"]');
                    if (btn) { btn.click(); return 'clicked: ' + t.substring(0, 50); }
                }
            }
            return 'not found';
        }
    """)
    print(f"[Facebook] Composer: {result}", file=sys.stderr)
    await asyncio.sleep(3)

    # Type post text — use JS evaluate click to bypass overlay divs
    try:
        # Click via JS to bypass any overlay
        await fb_page.evaluate("""
            () => {
                const el = document.querySelector('div[contenteditable="true"][role="textbox"]')
                    || document.querySelector('div[contenteditable="true"]');
                if (el) { el.click(); el.focus(); return 'focused'; }
                return 'not found';
            }
        """)
        await asyncio.sleep(1)
        composer = fb_page.locator('div[contenteditable="true"][role="textbox"]').first
        if not await composer.is_visible(timeout=5000):
            composer = fb_page.locator('div[contenteditable="true"]').first
        # Use clipboard paste instead of typing char-by-char (much faster for long posts)
        await fb_page.evaluate(f"""
            () => {{
                const el = document.querySelector('div[contenteditable="true"][role="textbox"]')
                    || document.querySelector('div[contenteditable="true"]');
                if (!el) return;
                el.focus();
                const text = {json.dumps(post_text)};
                document.execCommand('insertText', false, text);
            }}
        """)
        await asyncio.sleep(1)
        print("[Facebook] Text typed.", file=sys.stderr)
    except Exception as e:
        print(f"[Facebook] Type error: {e}", file=sys.stderr)
        return False

    # Upload image — set_input_files() bypasses Finder dialog entirely
    if image_path:
        try:
            # Click Photo/video button to reveal file input inside composer
            await fb_page.evaluate("""
                () => {
                    const spans = Array.from(document.querySelectorAll('span'));
                    for (const s of spans) {
                        const t = s.textContent.trim();
                        if (t === 'Photo/video' || t === '\u1ea2nh/video' || t === 'Photo' || t === '\u1ea2nh') {
                            const btn = s.closest('[role="button"]');
                            if (btn) { btn.click(); return 'clicked'; }
                        }
                    }
                    return 'not found';
                }
            """)
            await asyncio.sleep(2)
            # Inject file directly — no OS dialog opens
            file_input = fb_page.locator('input[type="file"]').last
            if await file_input.count() > 0:
                await file_input.set_input_files(str(image_path))
                await asyncio.sleep(3)
                print("[Facebook] Image uploaded.", file=sys.stderr)
            else:
                print("[Facebook] No file input found — posting without image.", file=sys.stderr)
        except Exception as e:
            print(f"[Facebook] Image error: {e}", file=sys.stderr)

    if dry_run:
        print("[Facebook] DRY RUN — not clicking Post.", file=sys.stderr)
        return True

    await asyncio.sleep(2)

    # Click Post via JS to bypass overlay divs
    post_result = await fb_page.evaluate("""
        () => {
            const divs = Array.from(document.querySelectorAll('div[role="button"]'));
            for (const d of divs) {
                const t = d.textContent.trim();
                if (t === 'Post' || t === '\u0110\u0103ng') { d.click(); return 'clicked: ' + t; }
            }
            const aria = document.querySelectorAll('[aria-label="Post"], [aria-label="\u0110\u0103ng"]');
            if (aria.length > 0) { aria[0].click(); return 'clicked aria'; }
            return 'not found';
        }
    """)
    print(f"[Facebook] Post button: {post_result}", file=sys.stderr)
    await asyncio.sleep(5)
    return "clicked" in post_result


async def _post_x(context, post_text: str, image_path, dry_run: bool) -> bool:
    """Post to X (Twitter) via Playwright CDP."""
    x_page = None
    for page in context.pages:
        if "x.com" in page.url and "sw.js" not in page.url and "blob:" not in page.url:
            x_page = page
            break

    if not x_page:
        x_page = await context.new_page()
        await x_page.goto("https://x.com/home")
        await x_page.wait_for_load_state("networkidle", timeout=15000)

    await x_page.bring_to_front()
    await asyncio.sleep(2)

    # Open compose box
    try:
        compose = x_page.locator('[data-testid="tweetTextarea_0"]').first
        if not await compose.is_visible(timeout=3000):
            btn = x_page.locator('[data-testid="SideNav_NewTweet_Button"]').first
            await btn.click(timeout=5000)
            await asyncio.sleep(2)
            compose = x_page.locator('[data-testid="tweetTextarea_0"]').first
        await compose.click()
        await asyncio.sleep(1)
        await compose.type(post_text, delay=20)
        print("[X] Text typed.", file=sys.stderr)
    except Exception as e:
        print(f"[X] Compose error: {e}", file=sys.stderr)
        return False

    # Upload image — set_input_files() bypasses OS dialog
    if image_path:
        try:
            file_input = x_page.locator('input[data-testid="fileInput"]').first
            await file_input.set_input_files(str(image_path), timeout=5000)
            await asyncio.sleep(4)
            print("[X] Image uploaded.", file=sys.stderr)
        except Exception as e:
            print(f"[X] Image error: {e}", file=sys.stderr)

    if dry_run:
        print("[X] DRY RUN — not clicking Post.", file=sys.stderr)
        return True

    await asyncio.sleep(1)

    # Click Post via JS to bypass overlay divs
    await x_page.evaluate("""
        const btn = document.querySelector('[data-testid="tweetButtonInline"]')
                 || document.querySelector('[data-testid="tweetButton"]');
        if (btn) btn.click();
    """)
    await asyncio.sleep(4)
    print("[X] Post submitted.", file=sys.stderr)
    return True


async def _run_post(draft: dict, dry_run: bool, facebook: bool, x: bool) -> dict:
    """Connect to Chrome CDP and run posting."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium",
              file=sys.stderr)
        sys.exit(1)

    results = {"facebook": None, "x": None}
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()

        if facebook and draft["facebook"]:
            results["facebook"] = await _post_facebook(
                context, draft["facebook"], draft["image_path"], dry_run
            )
        if x and draft["twitter"]:
            results["x"] = await _post_x(
                context, draft["twitter"], draft["image_path"], dry_run
            )
        await browser.close()
    return results


def generate_agent_instructions(draft: dict, dry_run: bool = False,
                                facebook: bool = True, x: bool = True) -> str:
    """Legacy fallback: text instructions. Prefer running auto_post.py directly."""
    return (
        "# Auto-Post Instructions (legacy)\n"
        f"Title: {draft['title']}\nImage: {draft['image_path'] or 'none'}\n"
        "NOTE: Run auto_post.py directly for reliable Playwright CDP posting.\n"
        "      Image upload via set_input_files() bypasses Finder dialog.\n"
        "      JS evaluate() clicks bypass overlay-blocked buttons."
    )


POST_STATE_FILE = WORKSPACE / "posts" / "post-state.json"


def load_post_state() -> dict:
    """Load post state tracking (which slugs have been posted to which platforms)."""
    if POST_STATE_FILE.exists():
        try:
            return json.loads(POST_STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_post_state(state: dict):
    """Save post state to disk."""
    POST_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    POST_STATE_FILE.write_text(json.dumps(state, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Post approved content to Facebook and X via Playwright CDP")
    parser.add_argument("--draft", required=True, help="Path to approved draft markdown file")
    parser.add_argument("--facebook-only", action="store_true", help="Post to Facebook only")
    parser.add_argument("--x-only", action="store_true", help="Post to X only")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fill post content but do NOT click publish")
    parser.add_argument("--start-chrome", action="store_true",
                        help="Launch Chrome with CDP automatically before posting")
    parser.add_argument("--instructions-only", action="store_true",
                        help="Print legacy text instructions (no browser automation)")
    parser.add_argument("--force", action="store_true",
                        help="Ignore post state and post even if already posted")
    parser.add_argument("--output", help="(legacy) Save instructions to file")
    args = parser.parse_args()

    # Resolve draft path
    draft_path = Path(args.draft).resolve()
    if not draft_path.exists():
        draft_path = WORKSPACE / args.draft
    if not draft_path.exists():
        print(f"ERROR: Draft not found: {args.draft}", file=sys.stderr)
        sys.exit(1)

    draft = parse_draft(draft_path)
    if not draft["facebook"] and not draft["twitter"]:
        print("ERROR: No post content found in draft.", file=sys.stderr)
        sys.exit(1)

    # Load post state — prevent duplicate posts on retry
    slug = draft_path.stem
    state = load_post_state()
    slug_state = state.get(slug, {})

    do_facebook = not args.x_only
    do_x = not args.facebook_only

    if not args.force and not args.dry_run:
        if do_facebook and slug_state.get("facebook") == "success":
            print(f"[Facebook] Already posted (slug: {slug}). Use --force to repost.", file=sys.stderr)
            do_facebook = False
        if do_x and slug_state.get("x") == "success":
            print(f"[X] Already posted (slug: {slug}). Use --force to repost.", file=sys.stderr)
            do_x = False

    if not do_facebook and not do_x:
        print("Nothing to post — both platforms already done. Use --force to override.", file=sys.stderr)
        sys.exit(0)

    # Legacy instructions-only mode
    if args.instructions_only or args.output:
        text = generate_agent_instructions(draft, dry_run=args.dry_run,
                                           facebook=do_facebook, x=do_x)
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
            print(f"Instructions saved to: {args.output}", file=sys.stderr)
        else:
            print(text)
        return

    # Ensure Chrome CDP is available
    if args.start_chrome:
        if not start_chrome_cdp():
            sys.exit(1)
    elif not is_cdp_ready():
        print("ERROR: Chrome CDP not reachable at", CDP_URL, file=sys.stderr)
        print("Tip: use --start-chrome, or launch Chrome manually:", file=sys.stderr)
        print(f'  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \\', file=sys.stderr)
        print(f'    --remote-debugging-port={CDP_PORT} --user-data-dir="{CHROME_USER_DATA}" \\', file=sys.stderr)
        print(f'    --no-first-run "https://www.facebook.com"', file=sys.stderr)
        sys.exit(1)

    # Run Playwright posting
    results = asyncio.run(_run_post(draft, args.dry_run, do_facebook, do_x))

    print("\n=== POST RESULTS ===")
    if do_facebook:
        fb = results.get("facebook")
        print(f"Facebook: {'✅ SUCCESS' if fb else '❌ FAILED' if fb is False else '⏭ SKIPPED'}")
    if do_x:
        xr = results.get("x")
        print(f"X:        {'✅ SUCCESS' if xr else '❌ FAILED' if xr is False else '⏭ SKIPPED'}")

    # Save post state to prevent duplicates on retry
    if not args.dry_run:
        state = load_post_state()
        if slug not in state:
            state[slug] = {}
        if do_facebook and results.get("facebook"):
            state[slug]["facebook"] = "success"
        if do_x and results.get("x"):
            state[slug]["x"] = "success"
        save_post_state(state)

    if results.get("facebook") is False or results.get("x") is False:
        sys.exit(1)


if __name__ == "__main__":
    main()
