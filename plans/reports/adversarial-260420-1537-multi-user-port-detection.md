# Adversarial Review — Multi-User Port Detection

**Target:** uncommitted diff (`install.sh`, `instruction.txt`, `instruction-multi-user.txt`)
**Base:** commit `2a44392`
**Reviewer:** self, full context, three-stage adversarial pass
**Prior review:** `code-reviewer-260420-1151-multi-user-port-detection.md` (DONE_WITH_CONCERNS, EXPLICIT_PORT bug resolved in-session)

## Stage 1 — Spec Compliance: PASS

Plan decisions (plan.md) vs implementation — all honored:

| Locked decision | Implementation | Verdict |
|---|---|---|
| Scan range: 18789-18798, fail loud | `find_free_port` tries=10; `die` with `lsof` hint | ✓ |
| Probe via `/dev/tcp` builtin, no new dep | `is_port_free` uses `(exec 3<>/dev/tcp/...)` | ✓ |
| `--port N` probed, bump + warn | gated by `EXPLICIT_PORT`; scan still runs | ✓ |
| Reinstall stability: reuse free stored port | resolve_port reads `$cfg` via jq, gated on `EXPLICIT_PORT=0` | ✓ |
| New `instruction-multi-user.txt`, pointer in existing doc | Created (105 lines), pointer added after intro | ✓ |

Plan success criteria 1-4 verified via integration tests in-session.

## Stage 2 — Code Quality: PASS (after code-reviewer fix)

Prior `code-reviewer` report flagged one HIGH (EXPLICIT_PORT collision) — resolved this session via `EXPLICIT_PORT` flag + `parse_args` arms.

No new standards / perf / style issues on re-read.

## Stage 3 — Adversarial Red Team

Put on hostile hat; probed for breakage.

### Findings — applied fixes this session

| # | Severity | Finding | Resolution |
|---|---|---|---|
| 1 | LOW | Stored port range not validated. Tampered `openclaw.json` with `"port": 0`, `"port": 99999`, or injected strings could reach `is_port_free`. Numeric `case` catches shell chars but not out-of-range integers. | Added `[ "$existing" -lt 1 ] || [ "$existing" -gt 65535 ]` guard. Verified via fault-injection tests: 0, 99999, shell chars all fall through to clean scan. |
| 2 | LOW (cosmetic) | Die message range could overstate (`requested+9` when near 65535) since `find_free_port` caps at 65535. | Clamped `end` at 65535 before interpolating. |
| 3 | LOW | Doc recommended `openclaw gateway restart` — subcommand not verified to exist upstream. `openclaw gateway install` known idempotent (per install.sh:408 comment) and available. | Replaced with instruction to re-run `install.sh`. Keeps user on a known-working path. |

### Attacks attempted, confirmed safe

- **Command injection via crafted config:** `"port": "\"; rm -rf /; \""` — jq strips quotes, numeric `case` rejects anything with non-digits. `existing=""`. Tested, inert.
- **Symlink attack (config → /dev/random, /var/log, etc.):** jq errors, stderr suppressed, `|| true` absorbs, `existing=""`. Falls through.
- **fd 3 leak:** probe runs inside `( ... )` subshell; fd closes on subshell exit. Parent shell's fd 3 never opened by the probe. Cleanup `exec 3<&-` in parent is a defensive no-op.
- **Concurrent installers on same account:** pre-existing race in install.sh (timestamp-based backup, non-atomic config swap). Port detection adds no new exposure.
- **Loopback MITM / eavesdrop:** /dev/tcp is a kernel socket, loopback only. Not network-reachable.
- **Environment tampering of EXPLICIT_PORT:** local shell var, not exported, unset at start, only set by `parse_args` on the script's own argv. Not externally settable.

### Accepted risks (documented, not code)

- **TOCTOU** between probe and daemon bind — upstream `gateway install` surfaces "address in use" loudly. Already mentioned in troubleshooting.
- **Staggered installs** — User A offline while User B probes; both configs end up claiming 18789. First to launchd wins; loser re-runs `install.sh`. Doc covers this under "Can we install at the same time?".
- **Reinstall-stability breaks when user's own daemon is listening** (keep-data path). Resolving would require `lsof` or PID ownership check; out of scope per "no new deps" rule.
- **/dev/tcp disabled in a hardened bash build** — probe always returns "free", scan picks first port, daemon bind fails loudly. No silent corruption. Stock macOS bash 3.2 enables /dev/tcp; no known users on custom bashes.

### Fragility notes (not bugs)

- `is_port_free` hardcodes fd 3. If future install.sh code opens fd 3 around a call site, probe could close a foreign fd. Not an issue today; comment left in helper.
- `resolve_port` reinstall-stability path correctness depends on `maybe_reset_existing_install` running first (so a reset-then-reinstall reads a post-reset config, not a stale pre-reset one). Current `main()` ordering is correct. If that order ever changes, reinstall stability silently lies.

## Downstream Verification

All `$PORT` consumers pick up the resolved value (grep-verified):

- `backup_and_write_config` — writes `gateway.port` into JSON ✓
- `wait_for_healthz` — probes `http://127.0.0.1:$PORT/healthz` ✓
- `on_success` — prints final summary ✓

## Doc Quality

`instruction-multi-user.txt`:
- Voice matches `instruction.txt` (plain, numbered, no jargon) ✓
- 105 lines — 5 over the aspirational "<100" target, not meaningful ✓
- Cross-references `instruction.txt` for shared steps (DRY) ✓
- Troubleshooting grounded in observable installer output, not implementation ✓
- Post-fix: no longer promises unverified `openclaw gateway restart` subcommand ✓

`instruction.txt` edit: single-line pointer, correctly placed between intro and "BEFORE YOU START". Non-invasive.

## Final Verdict

**Status:** DONE
**Summary:** All adversarial findings actionable-and-applied. Explicit-port bug from prior review also resolved. Downstream behaviour unchanged by the 3 fixes this stage added. Ready to commit.

## Unresolved Questions

1. Does upstream `openclaw` ship a `gateway restart` subcommand? (Doc now sidesteps by recommending re-running `install.sh` — safe regardless, but worth knowing for future docs.)
2. If two users on the same Mac both need static ports (e.g. for documentation / script paste-ability), deterministic UID-based allocation would sidestep the staggered-install race. Explicitly rejected in brainstorm; flagging only if the race bites in practice.
