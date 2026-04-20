# Phase 01 — `install.sh` Port Auto-Detection

## Overview

**Priority:** P0 (blocks multi-user scenario entirely)
**Status:** pending
**Effort:** S (~30 LOC, 1 file)

Add port probing + scan-and-bump logic to `install.sh`. Default port still 18789; if busy, bump to 18790…18798. Fail with `lsof` hint if all 10 in use.

## Context Links

- Source: `install.sh` (current 627 lines)
- Related: `plan.md` (this plan) for decisions + risks
- Upstream port is read from `openclaw.json` `gateway.port` — no upstream change needed

## Key Insights

- `install.sh` already threads `$PORT` through config write, `wait_for_healthz`, and `on_success` summary. Just change `$PORT` before `backup_and_write_config`.
- Bash 3.2 supports `/dev/tcp/HOST/PORT` natively — probe is dependency-free.
- `ORIGINAL_OPENCLAW_HOME` is the dry-run-safe home path already captured in `main()` for reset probing. Reuse it for the reinstall-stability read so dry-runs don't clobber intent.
- The install script currently does not `require_cmd lsof`, so avoid adding it as a hard dep; `/dev/tcp` is enough.

## Requirements

### Functional

- R1: Default port remains 18789 when free.
- R2: If 18789 busy, try 18790…18798 and pick the first free one.
- R3: If `--port N` supplied, probe N first; if busy, probe N+1…N+9. Print a `[port]` warning whenever the chosen port differs from the requested one.
- R4: If existing `openclaw.json` has a `gateway.port` and that port is currently free, prefer it over scanning (reinstall stability).
- R5: If no free port in range, `die` with an `lsof -iTCP:START-END -sTCP:LISTEN` hint.
- R6: Resolved port flows through to `openclaw.json`, daemon start, healthz probe, success summary — unchanged paths.

### Non-functional

- Bash 3.2 compatible (stock macOS).
- Zero new binary deps.
- `--dry-run` shows the probe result without side effects.

## Architecture

Three new helpers + one `main()` call site:

```
main()
├── parse_args
├── ORIGINAL_OPENCLAW_HOME=$OPENCLAW_HOME   (already exists)
├── [dry-run home remap]                    (already exists)
├── preflight                               (already exists)
├── collect_secrets / validate_secrets      (already exists)
├── maybe_reset_existing_install            (already exists)
├── resolve_port                            ← NEW
│   ├── reuse_existing_port_if_free    ← NEW helper
│   └── find_free_port                 ← NEW helper
│       └── is_port_free               ← NEW helper
├── run_official_installer                  (already exists)
├── backup_and_write_config                 (already exists, uses updated $PORT)
├── start_daemon / wait_for_healthz         (already exists)
└── on_success                              (already exists, shows resolved $PORT)
```

## Related Code Files

- **Modify:** `install.sh`
  - Add: `is_port_free`, `find_free_port`, `resolve_port` functions
  - Modify: `main()` — insert `resolve_port` call between `maybe_reset_existing_install` and `run_official_installer`
  - Update: `usage()` — mention auto-scan behaviour under `--port N`
- **No other files touched in this phase.**

## Implementation Steps

### 1. Add `is_port_free` helper

Place after `require_cmd` (around line ~142). Uses bash `/dev/tcp` to attempt a connection; connect success = port busy.

```bash
is_port_free() {
  local port="$1"
  # Redirect bash to open a TCP socket. Success = a listener answered.
  # Suppress stderr so "Connection refused" (the happy path!) stays quiet.
  if (exec 3<>/dev/tcp/127.0.0.1/"$port") 2>/dev/null; then
    exec 3<&- 2>/dev/null    # close probe fd
    return 1                 # busy
  fi
  return 0                   # free
}
```

### 2. Add `find_free_port` helper

```bash
find_free_port() {
  local start="$1" tries="${2:-10}" i=0 p
  while [ "$i" -lt "$tries" ]; do
    p=$((start + i))
    [ "$p" -gt 65535 ] && break
    if is_port_free "$p"; then
      printf '%s\n' "$p"
      return 0
    fi
    i=$((i + 1))
  done
  return 1
}
```

### 3. Add `resolve_port` (the call site)

```bash
resolve_port() {
  local requested="$PORT"
  local home="${ORIGINAL_OPENCLAW_HOME:-$OPENCLAW_HOME}"
  local cfg="$home/openclaw.json"
  local existing=""

  # Reinstall stability: if an existing config has a still-free port, reuse it.
  # Only applies when user didn't explicitly override with --port.
  if [ "$requested" = "$DEFAULT_PORT" ] && [ -f "$cfg" ]; then
    existing="$(jq -r '.gateway.port // empty' "$cfg" 2>/dev/null || true)"
    case "$existing" in
      ''|*[!0-9]*) existing="" ;;
    esac
    if [ -n "$existing" ] && is_port_free "$existing"; then
      if [ "$existing" != "$requested" ]; then
        printf '[port] reusing previously-assigned port %s (from %s)\n' "$existing" "$cfg" >&2
      fi
      PORT="$existing"
      return 0
    fi
  fi

  local chosen
  if chosen="$(find_free_port "$requested" 10)"; then
    if [ "$chosen" != "$requested" ]; then
      printf '[port] %s is busy; using %s instead\n' "$requested" "$chosen" >&2
    fi
    PORT="$chosen"
  else
    local end=$((requested + 9))
    die "no free port in $requested-$end. Check 'lsof -iTCP:$requested-$end -sTCP:LISTEN' and free one up."
  fi
}
```

### 4. Wire into `main()`

Insert after `maybe_reset_existing_install`, before `run_official_installer`:

```bash
maybe_reset_existing_install
resolve_port                          # ← NEW
if [ "$DRY_RUN" -eq 1 ]; then
```

Rationale: after reset (which may delete the old config) so reinstall-stability only triggers when the user chose `--keep-data`. Before installer + config write so the resolved port is what everything downstream uses.

### 5. Update `usage()`

Adjust the `--port N` help line so it's honest:

```
  --port N       Preferred gateway port (default 18789). If busy, the
                 installer probes N..N+9 and picks the first free one.
```

Add a line in `Environment` / notes:

```
Multi-user Macs: each macOS account gets its own gateway port automatically.
See instruction-multi-user.txt for the full walk-through.
```

### 6. Verify downstream call sites

Grep confirms these already reference `$PORT` and will pick up the resolved value:

- `backup_and_write_config` — writes `gateway.port` into JSON
- `wait_for_healthz` — probes `127.0.0.1:$PORT/healthz`
- `on_success` — prints final summary

No changes needed.

## Todo List

- [ ] Add `is_port_free` after `require_cmd`
- [ ] Add `find_free_port` right below it
- [ ] Add `resolve_port` right below that
- [ ] Insert `resolve_port` call in `main()` after `maybe_reset_existing_install`
- [ ] Update `usage()` `--port` line + add multi-user pointer
- [ ] Manual test: run installer twice from different users on a Mac; confirm ports diverge
- [ ] Manual test: `nc -l 18789 &` then run installer; confirm bump to 18790 with `[port]` warning
- [ ] Manual test: reinstall with existing 18790 config; confirm port unchanged
- [ ] Manual test: `for p in 18789..18798; do nc -l $p & done` then run; confirm `die` with lsof hint
- [ ] `bash -n install.sh` passes (syntax check)
- [ ] `shellcheck install.sh` clean or only pre-existing warnings

## Success Criteria

1. `bash -n install.sh` returns 0.
2. Installer with free 18789 → writes `"port": 18789`, daemon healthy.
3. Installer with busy 18789 → prints `[port] 18789 is busy; using 18790 instead`, writes `"port": 18790`, daemon healthy on 18790.
4. Second installer run (same user, existing config on 18790, 18789 free) → reuses 18790, no bump message.
5. `--port 20000` with 20000 busy → bumps to 20001 with warning.
6. All 10 ports busy → `die` with exact `lsof -iTCP:18789-18798 -sTCP:LISTEN` hint.
7. No new shellcheck errors introduced.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `/dev/tcp` disabled in a hardened bash | Very low | Medium — probe errors silently, port picks wrong | Monitor reports; fall back to `lsof` probe if anyone hits it. |
| `jq -r '.gateway.port'` errors on corrupt config | Low | Low — `|| true` absorbs, existing="" → falls through to scan | OK as-is. |
| TOCTOU between probe and `openclaw gateway install` | Low | Medium — daemon fails "address in use" | Upstream surfaces it clearly; troubleshooting in phase 2 doc mentions it. |
| User runs two concurrent installers in the same second | Very low | Medium — both probe same free port | Document; retry is cheap. |

## Security Considerations

- Probe uses loopback only (`127.0.0.1`). No network-external exposure.
- Port selection doesn't weaken the gateway's `bind: "loopback"` posture.
- No new secrets, no new file writes outside existing paths.

## Next Steps

Phase 2 (doc) can start immediately — no file or knowledge dependency beyond this phase's decisions.
