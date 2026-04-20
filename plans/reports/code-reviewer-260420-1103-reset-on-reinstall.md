# Code Review — reset-on-reinstall (install.sh, README.md, instruction.txt)

**Branch:** main · **Files:** install.sh (+106), README.md (+4), instruction.txt (+5)
**Reviewer focus:** insertion order, bash 3.2 compat, TTY edges, partial-state, doc accuracy

---

## CRITICAL

### C1. Dry-run remap silently masks reset detection
`install.sh:552-555` rebinds `OPENCLAW_HOME` to a fresh `mktemp -d` whenever `--dry-run` is used with the default home AND no `OPENCLAW_HOME_OVERRIDE`. This runs **before** `maybe_reset_existing_install` (line 559), so the `[ -f "$OPENCLAW_HOME/openclaw.json" ]` probe always misses the user's real config. Result: `bash install.sh --dry-run --reset` on a real machine with `~/.openclaw/openclaw.json` present does NOT log the planned reset — it's effectively a no-op for the reset branch.

**Reproduction (verified):** With `HOME=$tmpdir` and `$tmpdir/.openclaw/openclaw.json` present, `bash install.sh --dry-run --reset` produces no `[dry-run] would run: openclaw reset...` line. Adding `OPENCLAW_HOME_OVERRIDE=$tmpdir/.openclaw` makes it appear.

**Why your T5 passed:** the user almost certainly used `OPENCLAW_HOME_OVERRIDE` for testing, which bypasses the remap. Production users won't.

**Impact:** dry-run preview misleads users into thinking there's no reset action queued. They run real install, get prompted (or auto-reset under `--reset`), and lose data they thought they previewed.

**Fix:** check the real config path BEFORE the dry-run remap, OR run `maybe_reset_existing_install` against the unremapped path. Cleanest:

```bash
main() {
  parse_args "$@"
  preflight
  collect_secrets
  validate_secrets
  maybe_reset_existing_install            # check real $OPENCLAW_HOME first
  if [ "$DRY_RUN" -eq 1 ] && [ -z "${OPENCLAW_HOME_OVERRIDE:-}" ] && [ "$OPENCLAW_HOME" = "$HOME/.openclaw" ]; then
    OPENCLAW_HOME="$(mktemp -d ...)"
    printf '[dry-run] OPENCLAW_HOME=%s\n' "$OPENCLAW_HOME" >&2
  fi
  ...
```

(Note this also implies `preflight` runs against the real path — it already does, so no behavior change there.)

Add a regression test row T5b: `HOME=$tmpdir OPENCLAW_HOME unset, $tmpdir/.openclaw/openclaw.json present, run bash install.sh --dry-run --reset → expect dry-run reset line`.

---

## HIGH

### H1. Non-numeric env vars trip arithmetic comparisons
`install.sh:30-31, 110, 231-232, 262`. `RESET="${OPENCLAW_RESET:-0}"` accepts the env value verbatim. If a user sets `OPENCLAW_RESET=true` (or `yes`, or `1 ` with a trailing space), the subsequent `[ "$RESET" -eq 1 ]` emits `[: true: integer expression expected` to stderr and evaluates false. The mutex check at line 110 silently misfires (no mutex error even if both are "truthy" non-numeric), and the decision logic at line 231 doesn't pick up `decision="reset"`. User sees confusing stderr noise + behavior different from documentation.

**Fix:** normalize at parse time:

```bash
case "${OPENCLAW_RESET:-0}" in
  1|true|yes|on) RESET=1 ;;
  *) RESET=0 ;;
esac
case "${OPENCLAW_KEEP_DATA:-0}" in
  1|true|yes|on) KEEP_DATA=1 ;;
  *) KEEP_DATA=0 ;;
esac
```

README documents `OPENCLAW_RESET=1` literally so strict-1 is technically defensible, but the failure mode is silent + ugly. Pick one and document it.

### H2. Partial-state risk: reset succeeds, reinstall fails
`install.sh:275-278` runs `openclaw reset --scope full --yes --non-interactive` then returns. `run_official_installer` runs next (line 563). If reset wipes credentials/skills/config and the reinstall then fails (network drop, upstream 5xx, broken proxy), the user is left with a stripped install and no inline recovery hint. The `die` message in `run_official_installer:286` says "official installer failed (url: ...)" but doesn't mention "your data was already wiped — restore from $OPENCLAW_HOME backup". The script's `backup_and_write_config` (line 333) also runs AFTER `run_official_installer`, so there's no automatic snapshot before reset.

**Fix options (pick one):**
- (preferred) Snapshot `$OPENCLAW_HOME/openclaw.json` to a `.pre-reset.bak.$ts` BEFORE calling `openclaw reset`. Cheap, reversible by hand, no behavior change on success.
- Or augment the `die` in `run_official_installer` with a conditional message when reset just ran: "openclaw reset succeeded but reinstall failed — original config saved at <backup>".

This was not in your test matrix. Add as T13.

---

## MEDIUM

### M1. `openclaw reset` exit codes are not contractually documented
Reviewed upstream docs: no public exit-code spec for `openclaw reset --scope full --yes --non-interactive`. The script's hard `die` on non-zero (line 275) is conservative-correct, but if the upstream CLI ever returns non-zero on benign warnings (e.g., daemon already stopped, no skills installed), every reinstall will abort with "openclaw reset failed". No fix today, but worth pinning the upstream version in docs and re-running T12 against any CLI version bump. Consider adding a `OPENCLAW_RESET_IGNORE_ERRORS=1` escape hatch if this bites in practice.

### M2. README contradicts behavior on `OPENCLAW_HOME_OVERRIDE`
`README.md` advertises `OPENCLAW_HOME` (line in env table) but `install.sh:12` actually consults `OPENCLAW_HOME_OVERRIDE` first. Pre-existing, not introduced by this PR — flagging because the dry-run mask in C1 hinges on this distinction and users will hit it while debugging the new flow. Out of scope to fix here, but note it.

### M3. `[info]`/`[warn]` prompt outputs split across `/dev/tty` and `>&2`
`maybe_reset_existing_install` writes the y/N prompt to `/dev/tty` (correct, matches `prompt_secret`) but the "no TTY" notice and "keeping existing data" both go to `>&2` (line 250, 256). When the user pipes stderr to a log (`bash install.sh 2>install.log`), they'll see the no-TTY skip message in the log but the prompt path leaves no audit trail. Minor; recommend mirroring decisions to stderr too:

```bash
y|Y|yes|YES) decision="reset"; printf '[info] user confirmed wipe\n' >&2 ;;
*)           decision="skip"; printf '[info] user declined wipe (default)\n' >&2 ;;
```

---

## LOW

### L1. `instruction.txt` ordering nit
`instruction.txt:100-103`: paragraph appears AFTER the two-question block but the actual prompt order is tokens-first, wipe-question-second. Re-reading shows "the installer also asks" implies "in addition to" the two — which is correct. Wording is fine, just confirm by reading the paragraph aloud after a tired user has already answered token prompts.

### L2. `resolve_openclaw_binary` duplicates search logic from `run_official_installer`
`install.sh:200-222` vs `:294-312`. DRY violation. Pre-existing pattern would be to extract a helper `find_openclaw_binary()` returning the path. Not blocking; YAGNI applies if no third caller appears.

### L3. Default-N comment placement
`install.sh:245-247`: comment is inside the `case` arm for the default branch. It's clear and in the right spot. No change needed — flagging as "checked, OK" per your question 7.

---

## Findings by severity

- **CRITICAL:** 1 (dry-run remap masks reset detection)
- **HIGH:** 2 (env normalization, partial-state risk)
- **MEDIUM:** 3 (exit-code contract, README/HOME naming, log audit)
- **LOW:** 3 (instruction phrasing, DRY duplication, comment placement)

## Bash 3.2 compatibility
Clean. Verified: `local prefix cand`, `${OPENCLAW_RESET:-0}`, `${BASH_SOURCE[0]:-}`, `[ -r /dev/tty ] && [ -w /dev/tty ]` all work under stock macOS bash 3.2.57. `shellcheck` clean per user.

## TTY probing
`[ -r /dev/tty ] && [ -w /dev/tty ]` correctly distinguishes:
- `bash <(curl ...)` with terminal → readable, prompt fires (correct)
- `curl ... | bash` with terminal → `/dev/tty` still resolves, prompt fires (correct)
- `ssh host bash install.sh </dev/null` (no PTY) → fails, skip path (correct)
- `install.command` double-click on macOS → Terminal.app PTY, prompt fires (correct)
- `sudo -u other bash install.sh` → depends on `/dev/tty` ownership; user's `other` will see "Permission denied" on `/dev/tty` open → correctly falls to skip path

No edge-case bugs in the probe itself.

## ensure_openclaw_on_path interaction
Reset wipes `$OPENCLAW_HOME` contents (per upstream `--scope full` docs). `run_official_installer` writes `$OPENCLAW_HOME/bin/openclaw` afresh. `ensure_openclaw_on_path` then sees `[ -x "$bin_dir/openclaw" ]` true and proceeds. Correct order — provided H2 (reinstall actually succeeds) holds.

## Documentation accuracy
- `README.md` flags table + env table: matches code.
- `instruction.txt`: matches the prompt's default-N behavior.
- One nit on `OPENCLAW_HOME` vs `OPENCLAW_HOME_OVERRIDE` (M2, pre-existing).

---

## Unresolved questions
1. Is the dry-run remap (lines 552-555) load-bearing for any scenario beyond "don't accidentally write to user's real ~/.openclaw"? If yes, the C1 fix needs to preserve that property — moving `maybe_reset_existing_install` before the remap is fine because reset is gated by the same dry-run check (line 269 logs but doesn't execute), so no real `~/.openclaw` is touched.
2. Does `openclaw reset --scope full` delete `$OPENCLAW_HOME/bin/openclaw` itself? If yes, H2 is more severe (no recoverable binary if reinstall fails). If no, H2 is config-only — still bad but bounded.
3. Should `--reset` in dry-run mode use the real `$OPENCLAW_HOME` for detection but the temp `$OPENCLAW_HOME` for everything else? That's the semantic the C1 fix implies.

---

**Status:** DONE_WITH_CONCERNS
**Summary:** 1 critical (dry-run remap silently masks reset detection in the most common preview scenario), 2 high (env normalization + partial-state recovery), 3 medium, 3 low. Bash 3.2 / TTY / shellcheck all clean.
**Concerns/Blockers:** C1 should block landing — fix is one-line reorder in `main()`. H1/H2 are recommended before next release but not blocking.
