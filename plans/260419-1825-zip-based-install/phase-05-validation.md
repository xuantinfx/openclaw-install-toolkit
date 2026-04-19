---
phase: 05
status: automated-done; live-e2e deferred
priority: high
effort: M
---

# Phase 05 — Manual validation

## Overview
End-to-end validation of the zip-based install flow. Packet capture confirms zero GitHub requests. Idempotency check on re-run. Both entry points exercised.

## Files
- No code changes. Produces: `plans/reports/validation-260419-{slug}.md` with findings.

## Requirements
- Access to a fresh macOS environment (VM, clean user account, or `OPENCLAW_HOME_OVERRIDE=/tmp/ocw-vN` + pre-reset of `~/.openclaw`).
- Real Telegram bot token + Anthropic API key (use the same test account used in earlier plans; do not commit).
- `tcpdump` or `nettop` to observe outbound connections.

## Implementation Steps

### 1. Build a test zip manually (out-of-band; build-zip.sh is separate task)
```bash
cd openclaw-toolkit
mkdir /tmp/ocw-zip-staging
cp install.sh install.command /tmp/ocw-zip-staging/
cp -R skills /tmp/ocw-zip-staging/skills
cd /tmp
zip -X -r openclaw-toolkit-test.zip ocw-zip-staging
```

### 2. Simulate user flow from a clean slate
```bash
# clean prior install
openclaw gateway uninstall 2>/dev/null || true
rm -rf ~/.openclaw
# unzip to a realistic location (with spaces to stress-test)
mkdir -p "$HOME/Downloads/Open Claw Test"
unzip /tmp/openclaw-toolkit-test.zip -d "$HOME/Downloads/Open Claw Test"
```

### 3. Run via primary entry point (drag-to-Terminal equivalent)
```bash
bash "$HOME/Downloads/Open Claw Test/ocw-zip-staging/install.sh"
```
Enter Telegram token + Anthropic key when prompted.

### 4. Packet capture during install
In a second terminal before step 3:
```bash
sudo tcpdump -i any -n 'host github.com or host raw.githubusercontent.com' 2>&1 | tee /tmp/ocw-netcap.log
```
After install completes, stop the capture. Grep for `xuantinfx` and `raw.githubusercontent.com` → must be **zero** matches.

### 5. Verify outcomes
- `openclaw --version` works in a new Terminal.
- `ls ~/.openclaw/skills/` shows `content-monitor/` (and any others shipped).
- `cat ~/.openclaw/skills/content-monitor/SKILL.md` — non-empty.
- `~/.openclaw/openclaw.json` exists with mode `0600`.
- Gateway healthz returns 200: `curl -sS http://127.0.0.1:18789/healthz`.
- Telegram: send "hi" to the bot → bot replies with pairing code.

### 6. Run secondary entry point (double-click)
Reset state (`rm -rf ~/.openclaw`, gateway uninstall). Double-click `install.command` from Finder. If Gatekeeper blocks: right-click → Open. Confirm flow runs to success.

### 7. Idempotency check (re-run on same machine)
Run `install.sh` a second time without cleanup. Enter same credentials. Confirm:
- `openclaw.json.bak.<timestamp>` created.
- `~/.openclaw/skills/content-monitor/` replaced cleanly (no duplicate dirs).
- No errors during gateway install.
- Bot still responds post-second-run.

### 8. Negative cases
- Delete `./skills/` from test zip, rerun → script should die with actionable error.
- Plant a symlink inside `./skills/` (e.g., `ln -s /etc/passwd skills/evil`) → script must refuse to install.
- Run from inside a git worktree (e.g., this repo) → must refuse with existing git-worktree guard.

### 9. Write validation report
Save to `plans/reports/validation-260419-zip-based-install.md` capturing:
- Test environment (macOS version, clean or shared account).
- Each scenario result (pass/fail + observations).
- Packet capture excerpt.
- Any UX papercuts found.

## Todo List
- [ ] Build test zip from working tree
- [ ] Reset state, unzip to path-with-spaces
- [ ] Run primary entry point; record terminal output
- [ ] Capture network traffic; grep for github hosts
- [ ] Verify all post-install artifacts (skills, config, gateway, Telegram)
- [ ] Reset + test `.command` double-click path + Gatekeeper workaround
- [ ] Re-run idempotency test
- [ ] Execute 3 negative cases (missing skills/, symlink, git worktree)
- [ ] Write validation report

## Success Criteria
- Primary + secondary entry points both succeed on clean macOS.
- Packet capture: zero `github.com` or `raw.githubusercontent.com` requests during install.
- Skills present + SKILL.md readable.
- Idempotent re-run succeeds with config backup.
- All three negative cases fail loudly with actionable error messages.

## Risks
- Gatekeeper behaviour varies by macOS version. Document exact OS version in validation report.
- `tcpdump` requires sudo — user's environment may need an alternative (`nettop`, Little Snitch log review).
- Shared Anthropic/Telegram accounts — leaving test state around. Revoke test bot tokens after validation if they are ephemeral.
