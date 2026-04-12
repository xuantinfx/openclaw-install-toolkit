#!/usr/bin/env python3
"""
generate_image.py - Generate professional photorealistic images via Google Gemini API.

Primary:  Nano Banana 2 (gemini-3.1-flash-image-preview) — best quality, 1080x1080
Fallback: Imagen 4 (imagen-4.0-generate-001) — $0.03/img
Fallback: Imagen 4 Fast (imagen-4.0-fast-generate-001) — $0.02/img

Rules:
  - Always photorealistic, never illustration/symbol/cartoon
  - Wide/mid shots only — no close-up faces to avoid deformation
  - Output: 1080x1080px (1:1) — optimal for Facebook + X

Usage:
  python3 generate_image.py --draft posts/drafts/personal-injury/slug-2026-04-05.md
  python3 generate_image.py --all-today
  python3 generate_image.py --prompt "custom prompt" --slug my-post --category personal-injury

Env:
  GOOGLE_AI_API_KEY  (required)

Output:
  posts/images/<category>/<slug>-<date>.jpg
"""

import os, sys, json, time, re, base64, argparse, datetime, urllib.request, urllib.error
from pathlib import Path

WORKSPACE  = Path(__file__).parent.parent.parent.parent
IMAGES_DIR = WORKSPACE / "posts" / "images"
DRAFTS_DIR = WORKSPACE / "posts" / "drafts"

GOOGLE_API_KEY = os.environ.get("GOOGLE_AI_API_KEY", "")
if not GOOGLE_API_KEY:
    print("ERROR: GOOGLE_AI_API_KEY not set. Add via: openclaw config set env.vars.GOOGLE_AI_API_KEY <key>", file=sys.stderr)
    sys.exit(1)
GEMINI_BASE    = "https://generativelanguage.googleapis.com/v1beta/models"

# ── Models ────────────────────────────────────────────────────────────────────
MODEL_NANO_BANANA_2 = "gemini-3.1-flash-image-preview"  # primary — best quality
MODEL_IMAGEN4       = "imagen-4.0-generate-001"          # fallback — $0.03/img
MODEL_IMAGEN4_FAST  = "imagen-4.0-fast-generate-001"     # fallback — $0.02/img

# ── Prompt templates — wide/mid shots, no close-up faces ─────────────────────
PROMPT_TEMPLATES = {
    "know_your_rights": [
        "Wide shot of a confident professional attorney standing in a modern law office, "
        "dark navy suit, large window with city view behind, reviewing a document folder, "
        "full body visible, professional corporate photography, natural window light, photorealistic",

        "Medium shot of two attorneys in professional attire discussing a case "
        "in a bright modern conference room, both seen from the side at mid-distance, "
        "city skyline through floor-to-ceiling windows, natural light, editorial photography, photorealistic",
    ],
    "faq": [
        "Medium-wide shot of an attorney and client seated across from each other "
        "at a consultation table in a modern law office, both figures visible from waist up, "
        "warm professional lighting, law books lining the wall behind, documentary photography, photorealistic",

        "Wide shot of a law office interior, attorney's hands resting on a desk "
        "with legal documents spread out, client's hands visible across the table, "
        "no close-up faces, focus on hands and documents, warm office lighting, photorealistic",
    ],
    "case_story": [
        "Wide establishing shot of a suburban intersection with a minor car accident, "
        "two cars stopped, a person standing beside their vehicle on a phone call from a distance, "
        "golden hour lighting, photojournalism style, realistic",

        "Medium-wide shot of a person in a hospital waiting room sitting alone, "
        "figure visible from mid-distance, soft overhead lighting, "
        "candid documentary photography, photorealistic",

        "Wide shot of an attorney in a dark suit walking through a marble courthouse hallway "
        "seen from behind at a distance, grand architecture, cinematic photography, photorealistic",
    ],
    "industry_news": [
        "Wide shot of a professional business meeting in a modern high-rise boardroom, "
        "multiple people in business suits seated around a large glass table from across the room, "
        "city skyline through full-height windows, natural diffused lighting, editorial photography, photorealistic",
    ],
    "hei_education": [
        "Wide lifestyle shot of a happy couple standing in front of their beautiful "
        "two-story suburban home seen from across the front yard, "
        "late afternoon golden hour sunlight, lush green lawn, full figures visible, "
        "lifestyle photography, photorealistic",

        "Medium-wide shot of a homeowner seated at a kitchen table reviewing documents "
        "with a laptop open, bright modern kitchen interior, figure visible from waist up, "
        "natural window light, lifestyle photography, photorealistic",
    ],
    "market_news": [
        "Wide shot of a real estate agent and couple touring a bright open-plan home interior, "
        "all three figures visible from mid-distance, large windows, afternoon sunlight, "
        "editorial real estate photography, photorealistic",

        "Wide aerial-style shot of an affluent California residential neighborhood, "
        "tree-lined streets, well-kept homes with manicured lawns, clear blue sky, "
        "no people in frame, real estate photography, golden hour, photorealistic",
    ],
    "tips": [
        "Medium-wide shot of a financial advisor showing a tablet to a homeowner couple "
        "in a bright modern living room, all three figures visible from mid-distance, "
        "natural soft light, trust and warmth in their posture, lifestyle photography, photorealistic",
    ],
}

FALLBACK_PROMPTS = {
    "personal-injury": (
        "Wide shot of a professional personal injury attorney standing confidently in a polished law office, "
        "full body visible, navy suit, natural window light, editorial portrait photography, photorealistic"
    ),
    "mortgage": (
        "Wide shot of a smiling homeowner couple on the front porch of their beautiful modern home, "
        "seen from across the yard, golden hour sunlight, lifestyle photography, photorealistic"
    ),
    "general": (
        "Wide shot of a professional business meeting in a bright modern boardroom, "
        "diverse team of professionals in business suits, city skyline backdrop, "
        "editorial photography, photorealistic"
    ),
}


def pick_prompt(category, theme):
    templates = PROMPT_TEMPLATES.get(theme)
    if templates:
        day_of_year = datetime.date.today().timetuple().tm_yday
        return templates[day_of_year % len(templates)]
    return FALLBACK_PROMPTS.get(category, FALLBACK_PROMPTS["general"])


# ── Google Gemini (Nano Banana) ───────────────────────────────────────────────
def generate_google_gemini(prompt, model_id):
    """generateContent endpoint — Nano Banana 2, outputs ~1080x1080."""
    url = f"{GEMINI_BASE}/{model_id}:generateContent?key={GOOGLE_API_KEY}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": f"{prompt} --ar 1:1 --size 1080x1080"}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
    }).encode()
    req = urllib.request.Request(url, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
    for part in resp.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if "inlineData" in part:
            return base64.b64decode(part["inlineData"]["data"])
    return None


# ── Google Imagen 4 ───────────────────────────────────────────────────────────
def generate_google_imagen(prompt, model_id):
    """predict endpoint — Imagen 4, 1:1 aspect ratio."""
    url = f"{GEMINI_BASE}/{model_id}:predict?key={GOOGLE_API_KEY}"
    payload = json.dumps({
        "instances": [{"prompt": prompt}],
        "parameters": {"sampleCount": 1, "aspectRatio": "1:1", "personGeneration": "allow_adult"}
    }).encode()
    req = urllib.request.Request(url, data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
    img_b64 = resp.get("predictions", [{}])[0].get("bytesBase64Encoded", "")
    return base64.b64decode(img_b64) if img_b64 else None


# ── Main generate ─────────────────────────────────────────────────────────────
def generate_image(prompt, slug, category, date_str):
    print(f"  Generating: {slug[:60]}...")
    print(f"  Prompt: {prompt[:80]}...")
    img_bytes = None

    # 1. Nano Banana 2 — primary
    try:
        print(f"  → Nano Banana 2 (Gemini 3.1 Flash Image, 1080x1080)...")
        img_bytes = generate_google_gemini(prompt, MODEL_NANO_BANANA_2)
        if img_bytes:
            print(f"  ✅ Nano Banana 2 success")
    except Exception as e:
        print(f"  ⚠️  Nano Banana 2 failed: {e}")

    # 2. Imagen 4 — fallback
    if not img_bytes:
        try:
            print(f"  → Fallback: Imagen 4 ($0.03/img)...")
            img_bytes = generate_google_imagen(prompt, MODEL_IMAGEN4)
            if img_bytes:
                print(f"  ✅ Imagen 4 success")
        except Exception as e:
            print(f"  ⚠️  Imagen 4 failed: {e}")

    # 3. Imagen 4 Fast — last resort
    if not img_bytes:
        try:
            print(f"  → Fallback: Imagen 4 Fast ($0.02/img)...")
            img_bytes = generate_google_imagen(prompt, MODEL_IMAGEN4_FAST)
            if img_bytes:
                print(f"  ✅ Imagen 4 Fast success")
        except Exception as e:
            print(f"  ⚠️  Imagen 4 Fast failed: {e}")

    if not img_bytes:
        print(f"  ❌ All providers failed. Check GOOGLE_AI_API_KEY and billing.")
        return None

    out_dir = IMAGES_DIR / category
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{slug}-{date_str}.jpg"
    out_file.write_bytes(img_bytes)
    print(f"  💾 Saved → {out_file.relative_to(WORKSPACE)} ({out_file.stat().st_size//1024}KB)")
    return out_file


def update_draft_with_image(draft_path, image_path):
    """Move image into same folder as draft, update draft with relative path."""
    draft = Path(draft_path)
    if not draft.exists():
        return
    # Move image to same folder as draft
    dest_image = draft.parent / image_path.name
    if image_path != dest_image:
        import shutil
        shutil.move(str(image_path), str(dest_image))
        image_path = dest_image
    content = draft.read_text()
    rel_path = image_path.name  # just filename since it's in same folder
    section = f"\n---\n\n# Generated Image\n\n`{rel_path}`\n\n> Generated by Google Nano Banana 2 / Imagen 4. Review before posting.\n"
    content = re.sub(r'\n---\n\n# Generated Image\n.*$', '', content, flags=re.DOTALL)
    draft.write_text(content + section)
    print(f"  📂 Image moved → {dest_image.relative_to(WORKSPACE)}")


def parse_draft_meta(draft_path):
    text = Path(draft_path).read_text()
    meta = {}
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            for line in text[3:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
    slug = meta.get("slug", "") or re.sub(r"-\d{4}-\d{2}-\d{2}$", "", Path(draft_path).stem)
    return meta.get("category", "general"), meta.get("theme", "know_your_rights"), slug


def process_draft(draft_path, date_str=None):
    date_str = date_str or datetime.date.today().isoformat()
    category, theme, slug = parse_draft_meta(draft_path)
    prompt = pick_prompt(category, theme)
    image_path = generate_image(prompt, slug, category, date_str)
    if image_path:
        update_draft_with_image(draft_path, image_path)
    return image_path


def process_all_today(date_str=None):
    date_str = date_str or datetime.date.today().isoformat()
    drafts = list(DRAFTS_DIR.rglob(f"*{date_str}.md"))
    if not drafts:
        print(f"No drafts found for {date_str}")
        return
    print(f"Found {len(drafts)} draft(s) for {date_str}")
    for d in drafts:
        if "# Generated Image" in d.read_text():
            print(f"  SKIP {d.name} (already has image)")
            continue
        process_draft(d, date_str)
        time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description="Generate images via Google Nano Banana 2 / Imagen 4")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--draft", help="Path to a draft .md file")
    group.add_argument("--all-today", action="store_true", help="Generate for all today's drafts")
    group.add_argument("--prompt", help="Custom prompt")
    parser.add_argument("--slug", help="Slug name (used with --prompt)")
    parser.add_argument("--category", default="general")
    parser.add_argument("--theme", default="industry_news")
    parser.add_argument("--date", help="Date override YYYY-MM-DD")
    args = parser.parse_args()

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    date_str = args.date or datetime.date.today().isoformat()

    if args.draft:
        process_draft(args.draft, date_str)
    elif args.all_today:
        process_all_today(date_str)
    elif args.prompt:
        generate_image(args.prompt, args.slug or "custom", args.category, date_str)


if __name__ == "__main__":
    main()
