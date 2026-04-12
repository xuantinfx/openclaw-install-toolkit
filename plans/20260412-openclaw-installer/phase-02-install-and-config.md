# Phase 2 — Run Official Installer + Write Config

## Overview
- **Priority:** P0
- **Status:** completed
- **Depends on:** phase-01
- Invoke upstream `install-cli.sh` then generate `~/.openclaw/openclaw.json` via `jq` with inlined secrets. Backup any existing config.

## Key Insights
- `curl | bash` is acceptable here only because we control the surrounding script; the user already chose this delivery model. Still pass `--proto '=https' --tlsv1.2` to mirror upstream recommendation.
- **Never** build JSON with string concatenation or heredocs when values contain user input — tokens can have `"` or `\` characters. `jq -n --arg ...` only.
- Backup format: `openclaw.json.bak.<UTC-ISO-timestamp>` → `openclaw.json.bak.20260412T153000Z`. Sortable, timezone-unambiguous.

## Requirements

### Functional
- Source installer URL: `${OPENCLAW_INSTALL_URL:-https://openclaw.ai/install-cli.sh}`.
- Pipe to `bash` via `curl -fsSL --proto '=https' --tlsv1.2`.
- After installer completes, verify `command -v openclaw` succeeds and `openclaw --version` exits 0.
- If `$OPENCLAW_HOME/openclaw.json` exists: `mv` to `openclaw.json.bak.$(date -u +%Y%m%dT%H%M%SZ)`.
- Write new `openclaw.json` using `jq -n` with these `--argjson port` and `--arg` bindings for `model`, `botToken`, `anthropicKey`.
- `chmod 0600 openclaw.json` immediately after write.

### Non-functional
- Write atomically: `jq ... > openclaw.json.tmp && mv openclaw.json.tmp openclaw.json`. Prevents half-written file on error.

## Architecture
```
run_official_installer()
    └── curl -fsSL --proto '=https' --tlsv1.2 "$OPENCLAW_INSTALL_URL" | bash

backup_and_write_config()
    ├── if [ -f openclaw.json ]; then mv to openclaw.json.bak.<ts>
    ├── jq -n --arg port --arg model --arg botToken --arg anthropicKey \
    │       '{ gateway: {...}, channels: {...}, agents: {...}, env: {...} }' \
    │       > openclaw.json.tmp
    ├── mv openclaw.json.tmp openclaw.json
    └── chmod 0600 openclaw.json
```

## Config Structure Written

```json
{
  "gateway": {
    "port": 19000,
    "bind": "127.0.0.1"
  },
  "agents": {
    "defaults": {
      "model": { "primary": "anthropic/claude-sonnet-4-6" }
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "<literal>"
    }
  },
  "env": {
    "ANTHROPIC_API_KEY": "<literal>"
  }
}
```

## Related Code Files

### Modify
- `install.sh` — add `run_official_installer` and `backup_and_write_config` functions, wire into `main`.

## Implementation Steps

1. Add `run_official_installer`:
   - `local url="${OPENCLAW_INSTALL_URL:-$DEFAULT_INSTALL_URL}"`
   - `curl -fsSL --proto '=https' --tlsv1.2 "$url" | bash` — capture exit via pipefail.
   - Post-check: `command -v openclaw >/dev/null || die "openclaw not on PATH after install"`.
   - `openclaw --version >/dev/null || die "openclaw --version failed"`.
2. Add `backup_and_write_config`:
   - `mkdir -p "$OPENCLAW_HOME"`.
   - If `[ -f "$OPENCLAW_HOME/openclaw.json" ]`: compute `ts=$(date -u +%Y%m%dT%H%M%SZ)`, `mv` to `openclaw.json.bak.$ts`, print backup path.
   - Build config:
     ```bash
     jq -n \
       --argjson port "$PORT" \
       --arg model "$MODEL" \
       --arg botToken "$TELEGRAM_BOT_TOKEN" \
       --arg anthropicKey "$ANTHROPIC_API_KEY" \
       '{
         gateway: { port: $port, bind: "127.0.0.1" },
         agents:  { defaults: { model: { primary: $model } } },
         channels:{ telegram: { enabled: true, botToken: $botToken } },
         env:     { ANTHROPIC_API_KEY: $anthropicKey }
       }' > "$OPENCLAW_HOME/openclaw.json.tmp"
     ```
   - `mv "$OPENCLAW_HOME/openclaw.json.tmp" "$OPENCLAW_HOME/openclaw.json"`.
   - `chmod 0600 "$OPENCLAW_HOME/openclaw.json"`.
3. Wire `main`: `preflight → collect_secrets → validate_secrets → run_official_installer → backup_and_write_config`.
4. Manual test with a stub installer URL (a local `file://` or `python3 -m http.server` serving a no-op script) to verify flow without requiring openclaw.ai.
5. Verify resulting config with `jq . openclaw.json` — must parse.

## Todo List
- [x] `run_official_installer` function
- [x] `backup_and_write_config` function with `jq -n --arg` pattern
- [x] Atomic write via `.tmp` + rename
- [x] `chmod 0600` enforced
- [x] Backup filename uses UTC ISO timestamp
- [x] Wire into `main` flow

## Success Criteria
- After running script against stub installer, `~/.openclaw/openclaw.json` exists, mode `0600`, valid JSON, contains exactly the 4 user inputs.
- Re-running creates `openclaw.json.bak.<ts>` with old content and overwrites `openclaw.json`.
- Special chars in tokens (e.g. a token with a backslash test) don't break JSON generation.

## Risks
- `curl | bash` failure partway through: upstream installer's own idempotency handles this — we don't try to recover.
- Race: two installs simultaneously. Out of scope; document as "do not run concurrent installers".
- `jq` not installed before phase-02 → already caught in phase-01 preflight.

## Security
- `openclaw.json` is the single plaintext-secret surface. `0600` mandatory. Print warning at end of install (phase-03).
- `jq -n --arg` ensures shell metacharacters in tokens can't cause injection.

## Next Steps
- Phase 3: start daemon, verify three endpoints.

## Completion
- **Tester Report** (`reports/tester-phase02-20260412.md`): 10/10 tests passing — all functions verified.
- **Reviewer Report** (`reports/reviewer-phase02-20260412.md`): 9.6/10 score, 0 critical/high issues — implementation solid, no blockers.
