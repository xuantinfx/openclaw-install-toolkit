---
status: complete
created: 2026-04-20
completed: 2026-04-20
slug: multi-user-install-port-detection
---

# Multi-User Install — Port Auto-Detection

## Goal

Let two+ macOS users on the same Mac each run `install.sh` without TCP port collisions on the gateway. Installer auto-picks a free port; a new instruction doc walks through the multi-user scenario.

## Context

- Brainstorm design: approved inline this session (see commit / chat for detail)
- Current install pins `DEFAULT_PORT=18789` — second user's daemon fails `wait_for_healthz`
- Each user already has isolated `$HOME/.openclaw/` + own launchd agent + own binary. **Only** the port is a shared resource.
- Upstream `openclaw gateway install` reads port from `openclaw.json`; no upstream change needed.

## Scope

**In:** port probing, scan-and-bump logic, reinstall-stability read, new instruction doc, one-line pointer in existing doc.
**Out:** UID-based deterministic ports, same-user-multiple-installs, port conflict detection at daemon start (upstream concern).

## Phases

| # | Phase | Status | File |
|---|-------|--------|------|
| 1 | `install.sh` port auto-detection | complete | [phase-01-install-script-port-detection.md](phase-01-install-script-port-detection.md) |
| 2 | `instruction-multi-user.txt` doc | complete | [phase-02-multi-user-instruction-doc.md](phase-02-multi-user-instruction-doc.md) |

## Dependencies

Phase 2 can start in parallel with Phase 1 — no file overlap. Manual test at the end covers both.

## Key Decisions (locked during brainstorm)

- **Scan range:** 18789 → 18798 (10 ports). Fail loudly if full.
- **Probe method:** `/dev/tcp/127.0.0.1/$port` via bash builtin (no new dep).
- **Override behaviour:** `--port N` still gets probed; auto-bump with a `[port]` warning if busy.
- **Reinstall stability:** if `openclaw.json` exists and its port is still free, reuse it.
- **Doc shape:** new `instruction-multi-user.txt`, short; existing `instruction.txt` gets a 1-line pointer.

## Success Criteria

1. User A runs installer → port 18789. User B (different macOS login) runs installer → port 18790. Both daemons healthy on their respective ports.
2. `--port 18789` with 18789 busy → script bumps + warns, does not fail silently.
3. Reinstall under same user with existing config → port unchanged.
4. All 10 ports busy → `die` with `lsof` hint.

## Risks

| Risk | Mitigation |
|------|------------|
| TOCTOU — free at probe, busy at daemon start | Upstream `gateway install` surfaces "address in use"; troubleshooting mentions it. |
| Staggered installs — User A offline during User B's probe, both persist 18789 | Documented; reinstall-stability partially covers next run. |
| `/dev/tcp` disabled in some hardened bash builds | macOS ships stock bash 3.2 with `/dev/tcp` enabled; no known users on modified bashes. |

## Out of Band

No tests in repo for `install.sh` (pure bash + curl piping). Manual verification only — documented in phase 1's success criteria.
