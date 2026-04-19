---
phase: 03
status: done
priority: high
effort: M
---

# Phase 03 — Rewrite instruction.txt

## Overview
Collapse STEP 2 (install) + STEP 5 (install skills) into a single "Unzip and run" step. Remove all `curl ... | bash` references. Document drag-to-Terminal (primary) + double-click (secondary) entry points. Add Gatekeeper + exec-bit-loss fallback notes. Keep STEP 1, 3, 4, 6, 7, 8 largely intact.

## Files
- Modify: `/Users/mac/Documents/AI project x a Kent/openclaw-toolkit/instruction.txt`

## Requirements
- Target audience: non-technical macOS user ("no coding background").
- Plain text, no markdown — matches current style.
- ~80 chars max line width — matches current file.
- Keep total length reasonable (current is 183 lines; aim similar or shorter).
- No references to GitHub URLs, curl commands, or tarballs.
- Document the Vietnamese-speaker-friendly (simple English) tone from the original.

## Implementation Steps

### 1. Keep BEFORE YOU START section unchanged
The "get bot token + Anthropic key" prep is identical.

### 2. Keep STEP 1 (Open Terminal)
No changes needed unless we adopt double-click as primary — we don't; primary is drag-to-Terminal which requires Terminal open.

### 3. Replace STEP 2 entirely
New STEP 2: "Unzip the toolkit and run the installer."

Text outline:
- "You received a file called `openclaw-toolkit.zip` via message. Double-click it to unzip. You'll get a folder with two files inside: `install.sh` and `install.command`, plus a `skills` folder."
- Entry point A (primary, bit-independent):
  1. Open Terminal (same as STEP 1).
  2. Type the word `bash` and a single space — do NOT press Enter.
  3. Drag the `install.sh` file from Finder into the Terminal window. The path will appear.
  4. Press Enter.
- Entry point B (double-click, may need Gatekeeper bypass first):
  1. Double-click `install.command`.
  2. If macOS says "cannot be opened because it is from an unidentified developer": close the dialog, right-click `install.command`, choose "Open", click "Open" in the confirmation.
- Then: "It will ask you two questions — Telegram bot token and Anthropic API key. Paste each one when asked and press Enter."
- End with: "Wait for it to finish. You'll see a success message when it's done."

### 4. DELETE STEP 5 entirely
Skills now install automatically as part of STEP 2. Renumber subsequent steps: STEP 6 → STEP 5, STEP 7 → STEP 6, STEP 8 → STEP 7.

### 5. Keep STEP 3, 4 (say hi + approve) unchanged
Same pairing flow — unaffected by zip delivery.

### 6. Update TROUBLESHOOTING section
Remove: "command not found when pasting a command" (no pasting now).
Add entries:
- `"Permission denied" when running install.sh` → "Open Terminal first, then type bash (with a space), then drag install.sh into Terminal, then press Enter."
- `install.command won't open (Gatekeeper)` → "Right-click install.command in Finder, choose Open, then click Open in the confirmation dialog."
- `Unzip didn't create a folder` → "Try a different unzip tool — on macOS, double-clicking the zip in Finder works reliably."

### 7. Keep KEEP THESE SAFE section unchanged

## Todo List
- [ ] Rewrite STEP 2 with both entry points
- [ ] Delete old STEP 5
- [ ] Renumber STEPs 6/7/8 → 5/6/7
- [ ] Remove curl-related troubleshooting, add zip/Gatekeeper entries
- [ ] Re-read full file end-to-end; confirm no dangling references to install-skill.sh or curl
- [ ] Keep under 200 lines total

## Success Criteria
- No mentions of `curl`, `github.com`, `install-skill.sh`, or `raw.githubusercontent.com`.
- Both entry points documented with exact keystrokes.
- Gatekeeper workaround + exec-bit fallback both present in TROUBLESHOOTING.
- Reads end-to-end as a coherent 7-step flow for a non-technical user.

## Risks
- Overly wordy instructions lose non-technical readers. Counter: keep exact-keystroke numbered lists, short sentences.
- Users confused by two entry points. Mitigation: label A as "easiest" / "recommended", put it first.
