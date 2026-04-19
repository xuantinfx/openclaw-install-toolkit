---
type: plan-review
plan: 260419-1825-zip-based-install
reviewed: 2026-04-19
verdict: GO with fixes
---

# Plan review — zip-based install flow

Scope: plan.md + phase-01..05 reviewed against current install.sh, install-skill.sh, instruction.txt, README.md, skills/.

## Verdict

**GO once Phase 01 dry-run placement + SCRIPT_DIR guard are fixed.** Otherwise solid: well-decomposed, honest accepted-risks section, predict-review captured, observable success criteria.

## Blocking issues

### B1. Phase 01 dry-run skips install_local_skills (contradicts its own success criteria)
Phase 01 step 3 puts the call "after verify_anthropic, before on_success". But `main()` in install.sh:375-400 returns early in `--dry-run` at line 393 — **before** `start_daemon`/`wait_for_healthz`/`verify_telegram`/`verify_anthropic`. So in dry-run, `install_local_skills` never runs, yet Phase 01 success criteria demand: `bash install.sh --dry-run ... → logs "would install 1 skill(s)"`.

**Fix options:**
- a) Call `install_local_skills` **before** the dry-run early-return (e.g., right after `backup_and_write_config` at line 388) — works in both modes.
- b) Duplicate a dry-run-only invocation inside the `--dry-run` branch.
- (a) is cleaner, also matches natural dependency order: skills don't need the daemon running, only `$OPENCLAW_HOME` existing (created by `backup_and_write_config`).

### B2. Phase 01 SCRIPT_DIR guard is unreliable
Phase 01 step "Risks" proposes: `if $SCRIPT_DIR contains '-' ... die`. A dash in a path is not a pipe indicator; `/Users/mac/Downloads/open-claw/` would trigger false positive. For pipe-to-bash, `BASH_SOURCE[0]` is typically empty string or `bash`, not a dash.

**Fix:** Detect pipe mode explicitly — `[ -z "${BASH_SOURCE[0]:-}" ] || [ "${BASH_SOURCE[0]}" = "bash" ] || [ "${BASH_SOURCE[0]}" = "-" ]` → die with "run install.sh from unzipped folder, not via pipe". Also: guard that `$SCRIPT_DIR/skills` resolves to a readable directory — if resolution fails (symlinked temp, stdin source), die actionably.

## Non-blocking (should fix before merge)

### N1. Phase 01 function-placement vs call-site wording is ambiguous
Step 2 says "Place between verify_anthropic() and ensure_openclaw_on_path() (around line 300)" — refers to *function definition* position. Step 3 says "insert call after verify_anthropic, before on_success" — call site in main(). Two different concerns, same line range — easy to mis-apply. Split into "Function definition: around line 300" and "Call site: in main(), after X" explicitly.

### N2. Phase 01 step 4 under-specified
"Optionally add a note" about `./skills/` source — drop "optionally". Add at least one `[skills]` log line on startup so users see what's about to happen. Already implied by step 2's "Log `[skills] installed <name>`" but no entry-banner.

### N3. Phase 02 Terminal-window-stays-open depends on user profile
Terminal.app "When the shell exits" profile defaults to "Close if exited cleanly". `read -p` holds the window until Enter; correct. But a user who changed that profile setting sees no pause — fine for MVP, worth a one-liner risk note.

### N4. Phase 03 entry-point A relabel suggestion (from predict-review)
Predict-review output (plan.md:62) already flagged: demote `.command` to fallback in happy-path STEP 2. Phase 03 still documents both at equal weight. Decide: single-path happy flow (drag-to-Terminal) with `.command` in TROUBLESHOOTING, OR two-path with clear "recommended" label. Plan currently says "label A as easiest" (phase-03 risks) but implementation steps don't enforce that ordering. Tighten step 3.

### N5. Phase 05 tcpdump host filter may under-capture
`tcpdump host github.com` resolves once at startup → filters by IP. GitHub rotates CDN IPs. For a correctness claim ("zero GitHub requests"), prefer broader capture then grep, or use `nettop -P -m tcp` and filter post-hoc. Alternatively, block egress at the firewall for github.com during install and assert exit code 0.

### N6. Phase 04 README rewrite outcome under-specified
Step 3 says "Likely changes: Remove ... Replace ..." — needs concrete acceptance criteria (e.g., "no `install-skill.sh` references, no GitHub curl URLs, quick-start references zip delivery"). Otherwise reviewer can't verify without opinion.

### N7. Missing note: `run_official_installer` still curls openclaw.ai
Plan's headline claim is "only runtime network call hits openclaw.ai + Telegram/Anthropic verify". Correctly reflected in install.sh:172. Worth an explicit reminder in Phase 01 that this curl is **preserved** (not a regression to fix) — prevents an implementer from over-reading "drop GitHub fetch" as "drop all curls".

### N8. Accepted-risk scope: install-cli.sh may itself hit github
Phase-05 packet capture asserts zero github traffic during install. But the openclaw.ai installer it downloads may internally curl github release assets. If that happens, capture will flag it. Either (a) whitelist the fact upfront in phase 05 ("openclaw.ai installer may hit github.com/openclaw/*; only `xuantinfx/*` is forbidden"), or (b) grep strictly for `xuantinfx` as the plan already hints at.

## Missing pieces

- **No Phase 00 for build-zip.sh** — plan.md:26 defers it; Phase 05 step 1 builds a throwaway zip manually. Acceptable for validation, but the real release pipeline still has no owner. Confirm build-zip is tracked separately.
- **No commit/PR cadence** — one big commit vs per-phase commits not specified. Per-phase is safer (phase-01 behaviour change vs phase-04 delete are independently reviewable).
- **No Shellcheck in the todo lists** — `bash -n` is mentioned (syntax only). Add `shellcheck install.sh install.command` as a cheap CI gate.

## Cross-references verified

- Plan's assumption that `$OPENCLAW_HOME/skills/` is safe to `rm -rf` matches current install-skill.sh:154.
- Skill-name regex `^[a-z0-9][a-z0-9_-]{0,63}$` matches install-skill.sh:83.
- Symlink rejection pattern matches install-skill.sh:111.
- `skills/content-monitor/SKILL.md` exists — Phase 01 assertion holds.
- `OPENCLAW_HOME_OVERRIDE` → `OPENCLAW_HOME` precedence matches install.sh:12.

## Unresolved questions

1. Is build-zip.sh tracked as a separate plan? If not, Phase 05 is validating against a zip layout no one else can reproduce.
2. Entry-point labeling (N4): single happy path or dual? Predict-review leans single; plan keeps dual.
3. Packet-capture scope (N8): `xuantinfx`-only or full `github.com`?
