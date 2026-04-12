# Phase 3 — Start Daemon + Three-Check Verification

## Overview
- **Priority:** P0
- **Status:** completed
- **Depends on:** phase-02
- Start/restart the OpenClaw daemon, then prove end-to-end success via three independent checks. Script exits 0 only if all three pass.

## Key Insights
- Upstream installer registers launchd (macOS) / systemd (Linux) service, but after a config change we still need to restart the daemon to pick it up. Using `openclaw gateway restart` is idempotent — works whether running or stopped.
- `/healthz` check confirms the daemon started and loaded config. But daemon up ≠ Telegram working — need live API pings against Telegram and Anthropic.
- Telegram `getMe` is the cheapest, safest token validation — doesn't send any message, just echoes bot identity back.
- Anthropic `GET /v1/models` returns 200 with a valid key, 401 otherwise. No token usage, no cost.

## Requirements

### Functional
- `openclaw gateway restart` (or equivalent) invoked after config write.
- Poll `GET http://127.0.0.1:<port>/healthz` every 1s for up to 30s; must return HTTP 200.
- Call `GET https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe`; parse JSON; `.ok` must be `true`. Capture `.result.username` for the success message.
- Call `GET https://api.anthropic.com/v1/models` with `x-api-key: $ANTHROPIC_API_KEY` and `anthropic-version: 2023-06-01`; HTTP status must be 200.
- If any check fails, print which one, the actionable remedy, and exit non-zero.
- On full success, print: `All green. Message @<botname> on Telegram.` plus the plaintext-secrets warning.

### Non-functional
- Verification must not log secrets. Use `curl -sS -o /tmp/...` with body discarded for Anthropic; for Telegram, parse with `jq` and only echo `.result.username`.
- Total verification wall-time cap: 45s (30s health + ~15s for external calls).

## Architecture
```
start_daemon()
    └── openclaw gateway restart   # safe whether running or not

verify()
    ├── wait_for_healthz   # 30s poll, 1s interval
    ├── verify_telegram    # getMe → .ok=true, capture username
    └── verify_anthropic   # /v1/models → HTTP 200

on_success(username)
    └── print next-steps + security warning
```

## Related Code Files

### Modify
- `install.sh` — add `start_daemon`, `wait_for_healthz`, `verify_telegram`, `verify_anthropic`, `on_success`; extend `main`.

## Implementation Steps

1. Add `start_daemon`:
   - `openclaw gateway restart` — if exit non-zero, `die "openclaw gateway restart failed"`.
2. Add `wait_for_healthz`:
   - Loop `i` from 1 to 30:
     - `if curl -fsS --max-time 5 "http://127.0.0.1:$PORT/healthz" -o /dev/null; then return 0; fi`
     - `sleep 1`
   - `die "gateway did not become healthy within 30s on port $PORT. Try: openclaw gateway status; lsof -i :$PORT"`.
3. Add `verify_telegram`:
   - `resp=$(curl -fsS --max-time 10 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe")` — `die` on curl failure.
   - `ok=$(printf '%s' "$resp" | jq -r '.ok')`
   - If `$ok` != `true`: `die "Telegram getMe failed — token invalid?"`.
   - `BOT_USERNAME=$(printf '%s' "$resp" | jq -r '.result.username')`.
4. Add `verify_anthropic`:
   - `status=$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' -H "x-api-key: $ANTHROPIC_API_KEY" -H 'anthropic-version: 2023-06-01' https://api.anthropic.com/v1/models)`.
   - If `$status` != `200`: `die "Anthropic API returned HTTP $status — key invalid?"`.
5. Add `on_success`:
   - Print green `✓` lines for each of the 3 checks.
   - Print: `Message @$BOT_USERNAME on Telegram to start chatting.`
   - Print security warning: `WARNING: ~/.openclaw/openclaw.json contains your bot token and API key in plaintext (mode 0600). Do not commit, share, or back up unencrypted.`
6. Wire `main`: after `backup_and_write_config` → `start_daemon → wait_for_healthz → verify_telegram → verify_anthropic → on_success`.
7. Manual test: full end-to-end with real tokens on a clean VM.

## Todo List
- [x] `start_daemon` (`openclaw gateway restart`)
- [x] `wait_for_healthz` 30s poll with --max-time and error hints
- [x] `verify_telegram` via `getMe`, capture username
- [x] `verify_anthropic` via `/v1/models` with --max-time
- [x] `on_success` final message + security warning
- [x] Wire end-to-end in `main`

## Success Criteria
- On a clean VM with valid tokens, script runs cleanly from zero to "message the bot" state in < 90s.
- With a deliberately-bad Telegram token (format-valid, not registered), `verify_telegram` fails with actionable message; script exits 1.
- With a bad Anthropic key, `verify_anthropic` fails with HTTP status in message; script exits 1.
- With port already bound, `wait_for_healthz` eventually times out and exits 1 with port in message.

## Risks
- Upstream rate limits on Telegram `getMe` or Anthropic `/v1/models` during rapid re-runs → acceptable; these endpoints are cheap.
- `openclaw gateway restart` command verified against upstream docs; idempotent across running/stopped states.
- `/healthz` path verified in upstream `docs/install/docker.md`; no path drift expected.

## Security
- Secrets in-memory only during verification; never written to logs, never passed on command line.
- Curl calls use HTTPS with cert verification (default).
- Warning message at end is the user's primary cue that they chose the inline-secrets path.

## Completion

**Tester Report:** [tester-phase03-20260412.md](./reports/tester-phase03-20260412.md) — 45/45 tests passing.

**Code Review:** [reviewer-phase03-20260412.md](./reports/reviewer-phase03-20260412.md) — 9.6/10, 0 critical/high. Two MEDIUM suggestions post-review applied:
- `wait_for_healthz` error message includes actionable hints (`openclaw gateway status`, `lsof -i :PORT`).
- `curl --max-time` added to all 3 external calls (install: 30s; Telegram: 10s; Anthropic: 10s) honoring 45s wall-time cap.

All 6 implementation tasks completed. Risks resolved via upstream doc verification.

## Next Steps
- Phase 4: shellcheck, CI smoke test, publishing to hosted URL.
