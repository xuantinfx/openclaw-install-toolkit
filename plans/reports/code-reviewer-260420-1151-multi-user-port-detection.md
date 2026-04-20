---
type: code-review
date: 2026-04-20
scope: install.sh + instruction-multi-user.txt + instruction.txt (multi-user port detection)
files: install.sh (lines 76-78, 177-240, 673), instruction-multi-user.txt (new), instruction.txt (lines 14-16)
status: DONE_WITH_CONCERNS
---

# Multi-user port auto-detection — review

## Critical
None.

## High — design ambiguity (your Q3)
**Explicit `--port 18789` is indistinguishable from default `--port 18789`.**
`resolve_port` gates the "reuse existing config port" branch on
`[ "$requested" = "$DEFAULT_PORT" ]` (install.sh:216). If a user explicitly
passes `--port 18789` and an existing `openclaw.json` lists `19000`, the
installer silently switches them to 19000 — contradicting the design brief
("always probe explicit --port"). Fix: add an `EXPLICIT_PORT=0/1` flag set in
`parse_args` for the `--port`/`--port=` arms, gate the reuse branch on
`[ "$EXPLICIT_PORT" -eq 0 ]` instead. Cheap, removes the ambiguity entirely.

## Medium
1. **Range message off-by-some near 65535.** `find_free_port` correctly breaks
   on `p > 65535`, but the die() at install.sh:238 still prints
   `requested-$((requested+9))` even when only e.g. 6 of those ports were
   probed. Cosmetic; clamp `end` to `min(requested+9, 65535)` for accuracy.
2. **Probe→write→start TOCTOU.** Two simultaneous installers on the same Mac
   can both pick the same port. Already called out in
   `instruction-multi-user.txt` lines 64-71. Acceptable for installer scope.

## Low
1. `is_port_free`: `exec 3<&- 2>/dev/null` runs inside a subshell that's
   about to exit — fd is reaped automatically. Harmless but redundant.
2. Probing a non-OpenClaw listener (e.g. Postgres on 18789) opens a TCP
   connection that gets logged on the other side. Loopback-only, single
   connect, immediate close — low impact, document-only if anything.

## Verified safe (your Qs)
- **Q1 bash correctness:** `set -euo pipefail` is suppressed inside the `if`
  condition — subshell non-zero exit doesn't trip ERR. `IFS=$'\n\t'` is fine
  since `find_free_port` output is a single token via `printf '%s\n'`. Quoting
  on `"$port"`, `"$start"`, `"$tries"`, `"$requested"`, `"$existing"` all
  correct. Works under `curl|bash` (no BASH_SOURCE dependency in new code).
- **Q3 jq malformed config:** `jq ... 2>/dev/null || true` swallows errors,
  then `case ''|*[!0-9]*` strips non-numeric garbage. Safe.
- **Q4 dry-run path:** `resolve_port` reads from
  `${ORIGINAL_OPENCLAW_HOME:-$OPENCLAW_HOME}` (install.sh:212), captured in
  `main()` BEFORE the mktemp remap. Correct, mirrors
  `maybe_reset_existing_install`.
- **Q5 doc voice:** matches `instruction.txt` register. "gateway service"
  (line 91) is the sole borderline term, immediately followed by a concrete
  command — acceptable.

## Positive
- Reinstall stability check is well-scoped (only when port wasn't overridden).
- Dependency-free `/dev/tcp` probe avoids new requirements.
- Error message includes actionable `lsof` hint.
- Multi-user doc anticipates the race + the cross-account confusion failure mode.

## Unresolved questions
1. Confirm intent on Q3: should `--port 18789` (explicitly typed) override an
   existing config's 19000, or honor reinstall stability? Spec says "always
   probe explicit --port" — current code can't tell explicit from default.
2. Is `[port] reusing previously-assigned port X` ever printed today? Branch
   at install.sh:222-224 only fires when `existing != requested`, but the
   reuse branch only runs when `requested == DEFAULT_PORT`, so the message
   triggers iff the previously-stored port differs from 18789 — fine, just
   confirm that's the intended trigger.

**Status:** DONE_WITH_CONCERNS
**Summary:** Bash is solid; one design-spec mismatch on explicit `--port` handling worth a small fix before ship.
**Concerns:** High-priority item: `--port 18789` (explicit) currently can't override an existing-config port due to `requested == DEFAULT_PORT` collision. One-line `EXPLICIT_PORT` flag fixes it.
