---
type: validation
plan: 260419-1825-zip-based-install
date: 2026-04-19
status: partial — automated checks PASS; live E2E deferred to owner
---

# Zip-based install — validation report

## Environment
- Host: macOS 15.4 (Darwin 24.4.0, arm64)
- Shell: bash 3.2.57 (stock macOS — matches Bash 3.2 compat target)
- Repo: /Users/mac/Documents/AI project x a Kent/openclaw-toolkit (git worktree)

## Automated scenarios — PASS

All executed with `--dry-run` to avoid touching a live gateway or real creds.
Each case staged `install.sh` + a synthetic `skills/` dir in `mktemp -d`.

| # | Scenario | Expected | Result |
|---|---|---|---|
| 1 | Happy path: valid `skills/test-fixture/SKILL.md` | `[dry-run] would install 1 skill(s)` | PASS |
| 2 | Missing `./skills/` next to script | die: `skills/ not found …` | PASS |
| 3 | 1 symlink planted under `./skills/` | die: `skills/ contains symlinks …` | PASS |
| 3b | 10,000 symlinks (pipefail+SIGPIPE adversarial case) | die: `skills/ contains symlinks …` | PASS (post-fix) |
| 4 | Skill dir missing `SKILL.md` | die: `skill '<n>' is missing SKILL.md …` | PASS |
| 5 | Run from inside git worktree (no OPENCLAW_HOME_OVERRIDE hack) | die: `git worktree` guard | PASS |
| 6 | Idempotent re-run: second dry-run on same OPENCLAW_HOME | `openclaw.json.bak.<ts>` present | PASS |
| 7 | Pipe-via-stdin with hostile `./skills/` in CWD (adversarial) | die: `cannot locate script directory` | PASS (post-fix) |

## Post-review fixes (2026-04-19 21:27)

Code review found two critical regressions inherited from the pre-zip design.
Both reproduced, fixed, and re-verified.

1. **Symlink guard bypass under `set -o pipefail` + SIGPIPE.** Old pattern
   `find … | read -r` inside `if` flipped to "false" when `find` wrote
   more than ~one-line's worth of output (read closed pipe → find got
   SIGPIPE → pipefail made pipeline exit 141 → `if` skipped the `die`).
   Fixed by replacing with `$(find … | wc -l | tr -d ' ')` → `wc` always
   reads to EOF, no SIGPIPE, portable across macOS/Linux.
2. **SCRIPT_DIR fallthrough to CWD under `curl|bash`.** Old guard relied
   on an empty `SCRIPT_DIR`, but `${BASH_SOURCE[0]:-$0}` resolved to
   `"bash"` → `dirname "bash"` = `"."` → `cd . && pwd` = caller's CWD.
   Fixed by only assigning `SCRIPT_DIR` when `BASH_SOURCE[0]` points at
   a real file; otherwise leave empty so the existing guard fires.

Also verified:
- `bash -n install.sh` — syntax clean
- `bash -n install.command` — syntax clean
- `git ls-files --stage install.command` → mode `100755` (exec bit preserved)
- `git grep install-skill` on live files → zero matches
- `git grep 'raw.githubusercontent.com/xuantinfx/openclaw-install-toolkit'` on live files → zero matches

## Deferred to owner — live E2E

Requires real creds + network capture + Gatekeeper; can't run inside Claude's sandbox.

- [ ] Build real zip via `scripts/build-zip.sh` (separate task per plan) OR stage manually:
      `zip -X -r openclaw-toolkit-test.zip install.sh install.command skills`
- [ ] Unzip to `~/Downloads/Open Claw Test/` (path with space stress test).
- [ ] Run primary entry point: `bash "$HOME/Downloads/Open Claw Test/install.sh"`.
      Enter real Telegram bot token + Anthropic key. Confirm:
        - `openclaw --version` works in new Terminal
        - `ls ~/.openclaw/skills/content-monitor/SKILL.md` exists
        - `~/.openclaw/openclaw.json` mode `0600`
        - `curl -sS http://127.0.0.1:18789/healthz` returns 200
        - Telegram: `hi` → bot replies with pairing code
- [ ] Packet capture:
      `sudo tcpdump -i any -n 'host github.com or host raw.githubusercontent.com' | tee /tmp/ocw-netcap.log`
      grep for `xuantinfx` and `raw.githubusercontent.com` → must be **zero** hits.
- [ ] Double-click `install.command` from Finder on a fresh user account.
      First run → Gatekeeper blocks → right-click → Open → confirm.
      Walk full flow to success.
- [ ] Idempotency on same machine: re-run primary path; confirm
      `openclaw.json.bak.<ts>` created + skill dir cleanly replaced.

## Unresolved questions

- `scripts/build-zip.sh` is out of scope here (plan.md:26). Until it exists, the
  exact zip top-level folder name is undecided. `install_local_skills()` is
  robust to any name because it resolves via `BASH_SOURCE[0]` — but the zip
  packager needs to commit to a layout before the end-user drag flow is
  documented with exact paths in `instruction.txt`.
- `install.command` exec bit: `git ls-tree` shows `100755`, but some zip tools
  on macOS (BetterZip, unarchiver with quirks) strip mode bits. Drag-to-Terminal
  fallback covers this; confirmed documented in `instruction.txt` troubleshooting.
- CI fixture no longer tests a `.command` wrapper — Phase 02's double-click
  flow is purely macOS/Finder UX, not CI-testable.
