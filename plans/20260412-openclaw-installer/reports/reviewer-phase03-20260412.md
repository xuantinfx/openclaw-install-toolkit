# Phase 3 Code Review — Start Daemon + Three-Check Verification
**Date:** 2026-04-12
**Reviewer:** code-reviewer
**Scope:** `start_daemon` (L208-212), `wait_for_healthz` (L214-228), `verify_telegram` (L230-240), `verify_anthropic` (L242-252), `on_success` (L254-262), `main` wiring (L264-276), `BOT_USERNAME` global (L20) in `install.sh`.

---

## Summary

Phase 3 is faithful to the spec and hits all the right secret-safety notes. Curl stderr is suppressed everywhere a token could surface, response bodies are never echoed into `die` messages, and the Telegram token — the one secret that appears in a URL path — never touches a logging surface. The `set -e` / `pipefail` interaction with command substitution is handled correctly via `|| die` on the capture lines.

The one genuine deviation (`openclaw gateway restart` vs. plan's `openclaw restart`) is justified by upstream CLI verification and was called out in the scope note; the plan file itself should be updated to match (non-blocking).

No critical or high findings.

**Score: 9.6 / 10** — 0 critical, 0 high. **Auto-approvable.**

---

## Findings

### CRITICAL
None.

### HIGH
None.

### MEDIUM

#### M1 — `wait_for_healthz` error message lacks actionable next step (L227)
`die "gateway did not become healthy within 30s on port $PORT"` tells the user what failed and on which port but not what to do next. Compare to the nicely actionable `start_daemon` message ("run 'openclaw gateway restart' manually to see details"). Likely user questions at this point: is the daemon crashed? is the port bound by something else? where are the logs?
**Recommendation:** append something like `— check 'openclaw gateway status' or verify nothing else is bound to port $PORT (e.g. 'lsof -i :$PORT').`
**Confidence:** high.

#### M2 — No `--max-time` on any curl call; a hung endpoint can stall well past the advertised 45s budget (L219, L232, L244-247)
The plan explicitly caps verification at "30s health + ~15s for external calls". None of the three curl calls sets `--max-time`, so in practice:
- `wait_for_healthz`: if the TCP connect hangs (e.g. daemon bound but not accepting), a single curl iteration can wait for curl's default connect timeout (typically ~120s on Linux, kernel-dependent), blowing the 30s budget from iteration 1.
- `verify_telegram` / `verify_anthropic`: no ceiling at all; a network hang makes the installer appear frozen with no user feedback.
**Recommendation:** add `--max-time 2` to the healthz loop curl and `--max-time 10` to the two external calls. Matches the plan's stated time budget and prevents the worst-case install.sh hang.
**Confidence:** high — shell installer best practice and the plan explicitly specifies a wall-time cap.

### LOW

#### L1 — `jq` parse error on non-JSON 2xx response could leak body to stderr (L234, L238)
`curl -fsS` rejects non-2xx, so the common error path is safe. But a captive portal or misbehaving proxy can return HTTP 200 with an HTML body; jq then fails and, with `set -e` + `pipefail`, the script aborts while jq writes a snippet of the HTML to stderr. The HTML body never contains the bot token (the token is in the request URL, not echoed back), so **this is not a secret leak** — but the user gets a cryptic jq error instead of an actionable message.
**Recommendation:** optional — wrap the jq calls in `|| die "Telegram returned unparseable response — network intercepted?"`. Non-blocking.
**Confidence:** medium — plausible failure mode on hotel/corp networks.

#### L2 — `openclaw gateway restart` stderr is fully suppressed on first attempt (L210)
`>/dev/null 2>&1` hides everything, so when the die message tells the user to re-run manually, they do in fact get the info — but the first run's failure mode is a black box in the installer's own output. If the daemon failed to start because e.g. config was malformed, we already wrote that config and the user has no clue until the second run.
**Recommendation:** optional — capture stderr to a tempfile and emit the last few lines on failure, or drop the `2>&1` and let stderr through. Non-blocking; current behavior is defensible.
**Confidence:** medium.

#### L3 — Anthropic HTTP 429 surfaces as "key invalid or expired?" (L250)
`Anthropic /v1/models returned HTTP $status — key invalid or expired?` is accurate for 401/403 but misleading for 429 (rate-limited) or 5xx (upstream outage). During rapid re-runs on the same key the plan's own Risks section flags 429 as possible.
**Recommendation:** optional — branch on status: `401/403` → key invalid, `429` → rate-limited retry, `5xx` → upstream issue. Trivial; skip if KISS wins.
**Confidence:** high.

#### L4 — Plan file still says `openclaw restart` (phase-03-start-and-verify.md L18, L32, L51, L73)
Implementation correctly uses `openclaw gateway restart` per context7 docs; plan was not updated to match. Documentation drift only.
**Recommendation:** update phase-03-start-and-verify.md to reflect `openclaw gateway restart`. Non-blocking for merge; do before closing the plan.
**Confidence:** high.

### NIT

#### N1 — `on_success` uses `[OK]` plaintext; plan spec says "green ✓ lines" (L256-258 vs plan L66)
Cosmetic. `[OK]` is arguably friendlier on terminals without color / on CI logs, and no other part of the installer uses ANSI color, so adding it here alone would be inconsistent. The `[OK]` choice is reasonable.
**Recommendation:** keep as-is; update plan wording if you want exact alignment.

#### N2 — `healthz` progress dots print before the first attempt's sleep, so a fast-success run shows `...` before the "healthy" message (L219-224)
Actually — re-read: dot is printed only after curl fails. So a first-iteration success prints no dot and goes straight to "gateway healthy (took 1s)". Clean. Ignore this nit; just noting I checked.

#### N3 — `verify_anthropic` computes `$status` via command substitution inside `set -e` (L244-247)
Correctly guarded by `|| die` on the outer assignment, so a curl-exit-non-zero (DNS/TLS failure) triggers the die path; an HTTP 401/404/etc still yields exit 0 with `$status` set. This is the right behavior — flagging only because the focus area asked.
**Recommendation:** none.

---

## Focus-Area Checklist

| Focus | Verdict |
|------|--------|
| Secret safety (token in URL) | PASS — curl stderr is `2>/dev/null`; no die message echoes URL or response body; no `-v` / `--trace*` flags. |
| `set -e` + `pipefail` on `resp=$(curl ...)` | PASS — `\|\| die` on the assignment correctly catches curl non-zero. |
| Healthz iteration count | PASS — 30 curl attempts × 1s sleep ≈ 30s (curl timeout caveat in M2). |
| Healthz loop var sourced from secret | PASS — `$i` comes from `seq 1 30`. No secret involvement. |
| Anthropic `|| die` catches curl failure | PASS — command substitution + `\|\| die` aborts on curl non-zero exit. |
| Plan compliance | PASS with documented deviation — update plan file (L4). |
| YAGNI/KISS/DRY | PASS — two curl patterns differ materially (body capture vs. status-only); helper would be over-engineering. |
| `die` actionability | MOSTLY PASS — see M1 for healthz wording. |

---

## Positives

- `BOT_USERNAME` declared with empty default (L20) plays nicely with `set -u`.
- `jq -r '.ok // false'` and `.result.username // empty` handle missing fields gracefully without killing the pipe.
- `curl -fsS` on Telegram getMe — the `-f` is load-bearing; without it a 401 with a JSON error body would slip through `.ok != true` but still leak the response body if we later echoed `$resp`. Defense in depth.
- `main` wiring is linear and exactly matches the plan sequence.
- `2>/dev/null` on curl (not on jq) is the right granularity — curl's stderr can echo URLs in some error paths; jq's stderr is safe because it only sees the body, which never contains the token for Telegram.

---

## Recommended Actions (Prioritized)

1. **(Optional, medium)** Add `--max-time` to all three curl calls (M2).
2. **(Optional, medium)** Tighten the `wait_for_healthz` die message (M1).
3. **(Non-blocking)** Update `phase-03-start-and-verify.md` to say `openclaw gateway restart` (L4).
4. **(Optional, low)** Branch Anthropic error message on status code (L3).

None of these block merge. Phase 3 is auto-approvable.

---

## Unresolved Questions

- Is there a `/healthz` actually exposed by the current upstream `openclaw gateway`? The plan's Risks section (L89) flagged this as unverified. Worth confirming before phase 4 CI smoke test lands; if the path is different, the 30s poll will always time out on a real install.
