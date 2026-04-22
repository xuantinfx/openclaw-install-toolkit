# Content Monitor — Posting Flow

**This prompt defines the step-by-step flow from morning briefing to published post. The agent MUST follow every step and MUST confirm + guide the user to the next step after each one. NEVER go silent.**

## When to run

When the daily pipeline runs (via cron or manually via "run content pipeline"), or when the user says "what should I post today", "morning briefing", or "suggest today's content".

## MANDATORY RULES

- **After EVERY step: tell the user what was done and what the next step is**
- **NEVER go silent after completing a step** — always guide the user to the next action
- **Wait for user input where marked** — do not auto-proceed past approval gates
- **If something fails: explain the error and suggest a fix**

---

## Step 1: Run Pipeline + Send Briefing

Run the pipeline scripts:
```bash
source ~/.openclaw/workspace/.env-content-monitor
python3 scripts/news_fetch.py --auto
python3 scripts/suggest_daily.py --record
python3 scripts/social_draft.py --from-calendar
```

Then present the briefing to the user:

> 📋 **Today's Content Candidates**
>
> **Post 1** — [CATEGORY] | [THEME] | Source: [news/competitor/evergreen]
> Title: [TITLE]
> [Facebook post preview — first 200 chars...]
> X: [X post preview]
>
> **Post 2** — [CATEGORY] | [THEME] | Source: [news/competitor/evergreen]
> Title: [TITLE]
> [Facebook post preview — first 200 chars...]
> X: [X post preview]
>
> Which post do you want to use? Reply with the number (e.g. "1"), or "both" to use all.

**Wait for user to pick a post. Do NOT proceed until user replies.**

---

## Step 2: Generate Image

After user picks a post:

```bash
GOOGLE_AI_API_KEY=<key> python3 scripts/generate_image.py --draft <path-to-selected-draft>
```

Then show the result:

> ✅ **Image generated for: [Post Title]**
>
> [Send the image to the user — via Telegram or inline]
>
> Here's the full post for review:
>
> ---
> **Facebook Post:**
> [full Facebook post text]
>
> ---
> **X Post:**
> [full X post text]
>
> ---
>
> Does this look good? Options:
> - **"approve"** — I'll post it to Facebook and X
> - **"edit [instructions]"** — tell me what to change (e.g. "make it shorter", "change the tone")
> - **"regenerate image"** — generate a new image
> - **"skip"** — cancel this post

**Wait for user response. Do NOT proceed until user says "approve" or gives instructions.**

---

## Step 3: Handle User Response

**If user says "approve":**
- Say: "Great! Moving to posting. I'll post to Facebook first, then X."
- Proceed to Step 4.

**If user says "edit [something]":**
- Make the requested edits to the post text
- Show the updated version
- Ask again: "Updated. Does this look good now? Say 'approve' to post."
- Stay in Step 3 until user approves.

**If user says "regenerate image":**
- Generate a new image
- Show it to the user
- Ask again: "Here's the new image. Approve?"
- Stay in Step 3 until user approves.

**If user says "skip":**
- Say: "Post cancelled. Want me to show the other candidates instead?"
- If yes, go back to Step 1 briefing.
- If no, done.

---

## Step 4: Approve + Prepare Auto-Post

Run:
```bash
python3 scripts/approve_post.py --draft <path> --auto-post
```

This moves the draft + image to `posts/approved/` and generates `AUTO-POST-INSTRUCTIONS.md`.

Say:

> ✅ **Post approved and ready to publish.**
>
> I'll now post to your social media accounts:
> 1. First: Facebook
> 2. Then: X (Twitter)
>
> Starting with Facebook now...

**Proceed directly to Step 5. Do NOT wait — user already approved.**

---

## Step 5: Post to Facebook

Run auto_post.py trực tiếp (Playwright CDP):

```bash
source ~/.openclaw/workspace/.env-content-monitor
python3 scripts/auto_post.py --draft <approved-draft-path> --facebook-only
```

> **Lưu ý kỹ thuật quan trọng:**
> - Script dùng `set_input_files()` để inject ảnh trực tiếp vào `<input type="file">` — **KHÔNG** mở Finder dialog
> - Dùng `page.evaluate()` JS click để bypass overlay divs chặn Playwright click trên nút Post
> - Tìm composer bằng text JS search (`"What's on your mind"` / `"đang nghĩ"`) thay vì CSS selector
> - Chi tiết: xem `references/browser-autopost-working-method.md`

**Yêu cầu trước khi chạy:**
- Chrome đang chạy với CDP tại port 18800 và đã đăng nhập Facebook
- Nếu Chrome chưa mở: thêm flag `--start-chrome` vào lệnh trên

**After posting (or if it fails), say:**

If success:
> ✅ **Facebook: Posted successfully!**
>
> Now posting to X (Twitter)...

If failed:
> ❌ **Facebook posting failed.** [Error description]
>
> Options:
> - **"retry facebook"** — I'll try again
> - **"skip facebook"** — move on to X
> - **"post manually"** — I'll give you the text to copy-paste
>
> What would you like to do?

**If failed, wait for user response before proceeding.**

---

## Step 6: Post to X (Twitter)

Run auto_post.py trực tiếp (Playwright CDP):

```bash
source ~/.openclaw/workspace/.env-content-monitor
python3 scripts/auto_post.py --draft <approved-draft-path> --x-only
```

> **Lưu ý kỹ thuật:**
> - Dùng `set_input_files()` trên `input[data-testid="fileInput"]` để inject ảnh
> - Dùng JS `evaluate()` click nút Post để bypass overlay
> - Nếu X chưa mở tab: script tự navigate tới `https://x.com/home`

**After posting (or if it fails), say:**

If success:
> ✅ **X (Twitter): Posted successfully!**
>
> Both platforms done! Moving the post to the published archive...

If failed:
> ❌ **X posting failed.** [Error description]
>
> Options:
> - **"retry x"** — I'll try again
> - **"skip x"** — just archive the post
> - **"post manually"** — I'll give you the text to copy-paste
>
> What would you like to do?

**If failed, wait for user response before proceeding.**

---

## Step 7: Archive + Final Summary

Run:
```bash
python3 scripts/approve_post.py --publish <approved-folder>
```

This moves the post from `approved/` to `published/`.

**Always end with a summary:**

> 🎉 **All done! Here's the summary:**
>
> | Platform | Status |
> |---|---|
> | Facebook | ✅ Posted |
> | X (Twitter) | ✅ Posted |
>
> Post archived to `posts/published/[folder]`.
>
> Tomorrow I'll have new content candidates ready at [scheduled time].
> Say "run content pipeline" anytime to get more suggestions.

---

## Manual Post Fallback

If auto-posting fails and user says "post manually", provide:

> Here's your content to copy-paste:
>
> **Facebook** (copy everything below):
> ```
> [full Facebook post text]
> ```
>
> **X** (copy everything below):
> ```
> [full X post text]
> ```
>
> **Image**: saved at `[image path]`
>
> After you've posted manually, say "published" and I'll archive the files.

**Wait for user to say "published", then run Step 7 (archive).**

---

## Rules

- **NEVER go silent** — every step must end with a status + what happens next
- **NEVER auto-post without approval** — user must say "approve" first
- **If posting fails, offer 3 options**: retry, skip platform, or manual copy-paste
- **Show the full post text before approval** — user must see exactly what will be posted
- **One platform at a time** — post Facebook first, confirm, then X
- **Always archive at the end** — even if one platform was skipped
- **Always end with a summary** — what was posted, what was skipped, what's next
- **NEVER click "Photo/video" or any button that opens a native file picker dialog** — always use hidden `<input type="file">` via `browser_evaluate` + `browser_file_upload`. Native OS dialogs (Finder on macOS) cannot be automated and will get stuck.
- **If Finder/file dialog gets stuck open** — press Escape key via `browser_press_key` to close it before continuing
