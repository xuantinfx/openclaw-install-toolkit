# Phase 2 Code Review — Install + Config
**Date:** 2026-04-12
**Reviewer:** code-reviewer
**Scope:** `run_official_installer()` (L164-175), `backup_and_write_config()` (L177-205), `main()` wiring (L207-220) in `install.sh`.

---

## Summary

Phase 2 is tight, well-scoped, and faithful to the spec. The `jq -n --arg/--argjson` pattern, atomic `.tmp`+`mv`, `chmod 0600`, and UTC backup timestamp all match the plan. No critical or high-severity issues. A handful of low-severity robustness notes below.

**Score: 9.6 / 10** — 0 critical, 0 high. **Auto-approvable.**

---

## Findings

### MEDIUM

None.

### LOW

#### L1 — `jq` stderr on malformed arg could surface in logs (L190-200)
`jq` writes errors to stderr unsuppressed. If a future arg happens to be a malformed JSON fragment (e.g. `--argjson` on a non-integer), jq's stderr may print the bad value. Currently PORT is integer-validated in `parse_args`, so this is defense-in-depth only. Not a secret-leak today because the only `--argjson` input is the validated `PORT`. Safe for phase 2; worth re-auditing if new `--argjson` args are added.
**Recommendation:** keep as-is; document the invariant that only pre-validated values may be passed via `--argjson`.

#### L2 — Backup timestamp is second-precision; concurrent runs within 1s silently overwrite (L183-185)
`ts="$(date -u +%Y%m%dT%H%M%SZ)"` has 1-second resolution. Two `install.sh` invocations overlapping within the same wall-second would produce the same backup filename, and the second `mv "$cfg" "$backup"` would overwrite the first backup. Plan explicitly lists "concurrent installers" as out-of-scope (line 116), so this matches the spec.
**Recommendation:** none required. Optionally add `.${RANDOM}` or nanoseconds if future concurrency matters.

#### L3 — `.tmp` not cleaned on SIGINT/SIGTERM between redirection open and `|| { rm -f }` (L190-200)
If the user Ctrl-Cs between shell opening `$tmp` for `>` and `jq` finishing (or between `jq` success and the subsequent `mv`), a stale `openclaw.json.tmp` can remain. The EXIT trap only unsets env vars; it does not rm the tmp. Minor because the next run's `jq ... > "$tmp"` truncates it, and the file is mode 0600-effective once it exists.
**Recommendation:** optional — extend `cleanup()` to `rm -f "$OPENCLAW_HOME"/openclaw.json.tmp 2>/dev/null || true`.

### NIT

#### N1 — `eval` pattern in `prompt_secret` (L132, L142) is phase-1 code
Uses `eval "current=\${${var_name}:-}"` and `eval "$var_name=\$value"`. Safe today because `var_name` is only ever called with hardcoded literals (`TELEGRAM_BOT_TOKEN`, `ANTHROPIC_API_KEY`). Out of phase-2 scope; flagging only because phase 2 depends on it.
**Recommendation:** optional — switch to `printf -v` or namerefs (nameref needs bash 4.3+, which conflicts with the "Bash 3.2 compatible" header comment on L6). Keep as-is.

#### N2 — Plan internal inconsistency resolved correctly
`phase-02-install-and-config.md` line 21 says "`--arg` bindings: port, model, botToken, anthropicKey" but the Architecture block and code example (lines 82-93) use `--argjson port`. Implementation chose `--argjson port` (L191), which is the correct call — confirmed by tester (port stored as JSON number, not string). No action needed; consider tightening the plan text in a later cleanup.

#### N3 — No integrity check on piped installer (L168)
`curl | bash` with no checksum / signature verification is documented-and-accepted per plan L115 and L10. Not a review defect.

---

## Focus-area checklist

### 1. Bash safety (set -euo pipefail + curl | bash)
- `set -o pipefail` (L9) ensures curl's non-zero propagates through `| bash`. Verified.
- `|| die` on the pipeline short-circuits errexit cleanly — correct idiom.
- `IFS=$'\n\t'` set globally (L10); all user-controlled expansions in phase 2 are double-quoted (`"$url"`, `"$PORT"`, `"$TELEGRAM_BOT_TOKEN"`, `"$ANTHROPIC_API_KEY"`, `"$tmp"`, `"$cfg"`, `"$backup"`). No word-splitting or glob hazards.
- `command -v openclaw || die` and `openclaw --version || die` (L171-174) correctly disable errexit on the LHS.
**Verdict: clean.**

### 2. Injection / secret safety
- JSON built exclusively via `jq -n` with `--arg` / `--argjson` (L190-200). No heredoc, no `printf`-concatenated JSON. Verified by tester with hyphenated token.
- `die` messages (L169, L172, L174, L178, L185, L200, L202, L203) never echo `$TELEGRAM_BOT_TOKEN` or `$ANTHROPIC_API_KEY`. URL is the only external string echoed, which comes from env or the default constant.
- `printf '[install] fetching %s\n' "$url"` (L166) — format string is a literal; safe even if URL contains `%`.
- `cleanup` EXIT trap unsets both secret vars (L44). Fires on success and failure.
**Verdict: clean. No secret leakage path identified.**

### 3. Atomicity / cleanup
- `jq ... > "$tmp" || { rm -f "$tmp"; die ... }` (L190-200) — if `jq` fails after `>` opened `$tmp`, the cleanup runs. Reachable.
- `mv "$tmp" "$cfg" || { rm -f "$tmp"; die ... }` (L202) — reachable if rename fails (e.g. read-only target). Cleanup runs.
- `chmod 0600 "$cfg" || die` (L203) — by this point `$tmp` no longer exists; no leak possible.
- Gap: SIGINT between redirection and `jq` exit leaves `$tmp` (see L3 above). Minor.
**Verdict: atomicity solid; all three explicit error branches clean up.**

### 4. Plan compliance
| Spec item | Code | Match |
|---|---|---|
| URL env override `OPENCLAW_INSTALL_URL` w/ default | L165 | Yes |
| `curl -fsSL --proto '=https' --tlsv1.2 … \| bash` | L168 | Yes |
| Post-check `command -v openclaw` + `openclaw --version` | L171-174 | Yes |
| Backup on existing config | L181-187 | Yes |
| Backup name `openclaw.json.bak.<UTC ts>` | L183-184 | Yes |
| `jq -n` with `port/model/botToken/anthropicKey` | L190-200 | Yes (`--argjson port` per architecture block) |
| Atomic `.tmp` + `mv` | L189, L202 | Yes |
| `chmod 0600` | L203 | Yes |
| `main` order: preflight → collect → validate → install → config | L209-213 | Yes (`parse_args` prepended — reasonable) |
| Config shape (gateway/agents/channels/env) | L195-199 | Exact match |
**Verdict: compliant.**

### 5. YAGNI / KISS / DRY
- Two focused functions, no premature abstraction. No duplication with phase 1.
- No dead code introduced in phase 2.
- `mkdir -p "$OPENCLAW_HOME"` at L178 is slight overlap with phase-1 preflight's `$OPENCLAW_HOME` probe, but the probe does not create the dir, so this is correct, not duplicate.
**Verdict: lean.**

### 6. Failure clarity
- All `die` messages are actionable and include the offending path/URL.
- `openclaw not on PATH after install — check installer output above` (L172) correctly points the user upstream.
- No secret echoed in any error path.
**Verdict: good.**

---

## Positive observations
- `pipefail` + `|| die` on `curl | bash` is the textbook correct pattern; many wrappers get this wrong.
- `--argjson port` for numeric propagation + `--arg` for strings is exactly right.
- EXIT trap `unset`s secret env vars — nice defense-in-depth even though most users won't export them.
- Error branches on both `jq` redirect and `mv` are explicit rather than relying on `set -e` — much easier to reason about.
- UTC ISO timestamp (`%Y%m%dT%H%M%SZ`) is sortable and unambiguous, per plan.

---

## Recommended actions
1. **None blocking.** Proceed to phase 3.
2. Optional hardening (defer to later phase):
   - Extend `cleanup()` EXIT trap to `rm -f` stray `openclaw.json.tmp` (addresses L3).
   - Reconcile plan text at `phase-02-install-and-config.md` L21 to say `--argjson port, --arg model/botToken/anthropicKey` (addresses N2).

---

## Metrics
- Lines added in phase 2: ~42 (L164-205) + 2 call-site lines in `main`.
- Cyclomatic complexity: both new functions are linear; no nested conditionals beyond single `if -f`.
- Shellcheck: clean (per tester).
- Secret-exposure paths audited: 0 found.

## Unresolved questions
None.

## Status
**APPROVED — 9.6/10, auto-approvable.** Ready for phase 3.
