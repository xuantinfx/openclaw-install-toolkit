# Code Review — Phase 2 `install-skill.sh`

**Reviewer:** code-reviewer
**Date:** 2026-04-13
**File:** `install-skill.sh` (commit `c6ce7e0`)
**Spec:** `phase-02-install-skill-script.md`

## Scope
- 1 file, 149 LOC
- Public-facing `curl | bash` skill installer
- Verified empirically on stock macOS `/bin/bash 3.2.57`

## Overall Assessment
Solid, small, spec-compliant. Matches `install.sh` house style (`die`/`usage`/`require_cmd`, `set -euo pipefail`, `IFS=$'\n\t'`, `trap cleanup EXIT`). Bash 3.2 array usage is correct. Exec-bit preservation via `cp -R` confirmed on macOS. Main gap: **no validation that user-supplied skill names are safe identifiers**, which in the worst case enables path traversal outside `~/.openclaw/skills/`. One real behavior bug around `SKILL.md` validation for tarball-enumerated skills. Everything else is minor polish.

---

## Critical

### C1. Path traversal via crafted skill name argument
**Location:** `install_one` (lines 110–112), called from `main` loop

```
local src="$TARBALL_ROOT/skills/$skill"
local dst="$OPENCLAW_HOME/skills/$skill"
```

If a user runs `install-skill.sh '../../etc/pwnd'` (or more realistically: pastes a bad skill name from an untrusted source, e.g. a README exploit), `$skill` is substituted unvalidated into both paths. Empirically:

- `dst` resolves to `~/.openclaw/evil` — outside the `skills/` subtree.
- `rm -rf "$dst"` then operates on that resolved path. Attacker-controlled argv → arbitrary directory under `$OPENCLAW_HOME` gets deleted and replaced.
- The `[ -d "$src" ]` gate is not a real defense: if the tarball happens to be attacker-influenced (via `TOOLKIT_TARBALL_URL` override, documented env var), `$src` with `..` segments resolves to arbitrary locations inside the extracted tree or even into other parts of `$TMPDIR_INSTALL`.

Severity is **critical** because:
- The script is served via `curl | bash` and documented to take positional args (`bash -s name1 name2`).
- Users are trained to pipe it to shell from the net, so copy-paste of a malicious invocation is plausible.
- `rm -rf` on an unintended path is destructive and silent.

**Fix:** Validate each skill name against a strict identifier pattern **before** any filesystem work. Suggested placement in `parse_args` (after collecting) or at top of `install_one`:

```bash
case "$skill" in
  ''|.|..|*/*|*[!A-Za-z0-9_.-]*)
    die "invalid skill name: '$skill' (use [A-Za-z0-9_.-], no slashes)"
    ;;
esac
```

Also defensively clamp enumeration results: skills enumerated from the tarball come from `basename "$entry"` on a trailing-slash glob, which in practice cannot contain slashes — but applying the same validator to enumerated names too costs nothing and closes the loop against future refactors or attacker-influenced tarballs.

---

## Major

### M1. `install_one` skips `SKILL.md` check in dry-run-vs-enumerated mismatch, and the current check rejects valid tarballs with non-SKILL.md-root skills
**Location:** `install_one` lines 114–116

```
[ -f "$src/SKILL.md" ] \
  || die "skill '$skill' is missing SKILL.md at its root — corrupt toolkit?"
```

Two concerns:

1. **Hard `die` on first missing `SKILL.md`** kills the whole run mid-loop. If a user runs `install-skill.sh a b c` and `b` is malformed, `c` is never attempted and partial state is left on disk (`a` installed, `b`/`c` absent). Spec says "fail fast on missing" for positional args (reasonable), but enumeration mode (no args → install all) should arguably be more tolerant or at least report all failures at the end. Current behavior: one bad skill in the tarball breaks `install-skill.sh` entirely for every customer until fixed upstream.

2. **Case-sensitive `SKILL.md`** — OpenClaw skills in this repo use exactly that casing, fine today. Just flag that any future rename drift breaks customers silently after they pull.

**Fix options** (pick one):
- Collect failures into an array, continue installing the rest, non-zero exit with a summary at the end.
- Or explicitly document "installer is all-or-nothing; fix the upstream skill" and leave as-is. Either is defensible — just make the choice deliberate.

### M2. `find ... | head -1` is fragile against GitHub tarball variations
**Location:** `fetch_tarball` line 91

```
root="$(find "$TMPDIR_INSTALL" -mindepth 1 -maxdepth 1 -type d | head -1)"
```

Empirical check against the live tarball today shows a single top-level dir (`openclaw-install-toolkit-main/`). But:

- Some GitHub archive tarballs include a `pax_global_header` pseudo-entry. `tar -xz` silently consumes it (no real dir), so today it doesn't trip `-type d`. But if tarball format ever changes (release assets, signed tarballs) or a user overrides `TOOLKIT_TARBALL_URL` to a different shape, `head -1` silently picks whichever dir `find` returned first (order is filesystem-dependent, not alphabetical).
- `find` without `-print` uses newline separators; with `IFS=$'\n\t'` that's fine here, but worth noting.

**Fix:** Either tighten the match to the expected prefix, or assert exactly one top-level dir:

```bash
# Option A: expected-prefix match
root="$(find "$TMPDIR_INSTALL" -mindepth 1 -maxdepth 1 -type d -name '*-toolkit-*' -print | head -1)"

# Option B: assert uniqueness
local count
count="$(find "$TMPDIR_INSTALL" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
[ "$count" = "1" ] || die "unexpected tarball layout: $count top-level dirs"
```

### M3. Tarball symlinks are extracted with no sandboxing
**Location:** `fetch_tarball` line 86 (`tar -xz -C "$TMPDIR_INSTALL"`)

A malicious or compromised tarball can contain symlinks that point outside `$TMPDIR_INSTALL`, or use `../` in member paths. The extraction goes into a fresh `mktemp -d` so damage from `../` within extraction is confined to the tmpdir. **However**, the subsequent `cp -R "$src" "$dst"` follows symlinks — so a tarball containing `skills/foo/SKILL.md -> /etc/passwd` would cause a *read* of `/etc/passwd` and its content to be copied into `~/.openclaw/skills/foo/SKILL.md`. Not an escalation, but weird, and creates a path for a compromised upstream to tamper with user files within `~/.openclaw/`.

GNU tar has `--no-same-owner` and BSD tar (macOS) is reasonably safe re: absolute paths by default, but neither blocks relative-symlink content.

**Fix (belt-and-suspenders):**
- Add `--no-same-owner` to the `tar` invocation.
- Consider `cp -RP` (no-deref) instead of `cp -R` so symlinks inside skills are preserved as symlinks rather than dereferenced, AND add an explicit reject for any symlinks in `$src` during validation — skills shouldn't contain symlinks anyway. Cheap guard:

```bash
if find "$src" -type l | grep -q .; then
  die "skill '$skill' contains symlinks — rejecting for safety"
fi
```

Severity is "major" not "critical" because the threat requires a compromised toolkit repo (not a MITM — TLS pinning to `=https --tlsv1.2` is present), and the blast radius is limited to `$OPENCLAW_HOME` paths. Still worth the 3 lines.

---

## Minor

### m1. `OPENCLAW_HOME` preflight check is overly strict
**Location:** `preflight` lines 78–79

```
[ -d "$OPENCLAW_HOME" ] || die "$OPENCLAW_HOME not found — run install.sh first"
```

Matches spec. But `~/.openclaw/` existing doesn't actually mean `install.sh` has been run — it might be a stale directory. Error message is fine; no change needed. Flagging only because you may want a more meaningful sentinel file check later (e.g., `[ -f "$OPENCLAW_HOME/openclaw.json" ]` for "was install.sh actually completed").

### m2. Temp dir cleanup runs on EXIT but not on unexpected signals in old bash
**Location:** line 57 `trap cleanup EXIT`

`trap ... EXIT` catches normal exits and `set -e` failures. On `SIGTERM`/`SIGHUP`/`SIGINT` in bash 3.2 it's less reliable than one might assume — EXIT still fires on SIGINT (Ctrl-C) under `set -e`, but explicit coverage is cheap:

```bash
trap cleanup EXIT INT TERM HUP
```

Low priority; default behavior leaves a `/tmp/tmp.XXXXXX` dir on hard kill, not a real problem.

### m3. Usage string references env vars with literal `$HOME`
**Location:** `usage()` line 43

```
OPENCLAW_HOME         Override install root (default: $HOME/.openclaw)
```

The heredoc is quoted (`<<'EOF'`), so `$HOME` prints literally — which is what you want for docs. Fine. Just flagging that `install.sh` does the same. Consistent. No action.

### m4. `enumerate_skills` glob silently skips `.`-prefixed skill dirs
**Location:** lines 100–104

Empirically verified: `for entry in "$TARBALL_ROOT/skills"/*/` does not match `.hidden/`. This is desired (don't install hidden toolkit metadata dirs), but worth one line of comment since future-you might wonder.

### m5. `stdin` is not consumed by the script body, but the shebang + `bash -s` path is implicit
The script never reads from stdin; under `curl | bash -s foo bar`, the tarball body IS stdin to `bash`, and `bash` consumes it as the script text. The `-s` treats remaining args as positional. No issue. (Verified by inspection: no `read`, no `cat -`, no `</dev/stdin`.) Matches spec item 5.

### m6. No progress feedback during tarball fetch
`curl -fsSL` with `-s` suppresses progress. On a slow network, user sees only `[fetch] <url>` then silence. Minor UX wart; `curl -fSL` (without `-s`) would show a progress bar — but also pollutes non-TTY output. Leave as-is unless users complain.

### m7. `${#SKILLS[@]}` arithmetic under `set -u` with empty array
Verified on bash 3.2.57: `[ "${#SKILLS[@]}" -eq 0 ]` works correctly when array is empty (no unbound-var error). Spec note in phase doc expressed uncertainty — confirm this is fine. Nothing to change.

---

## Edge Cases Found by Scout

1. **Path traversal** via `install-skill.sh '../../evil'` → see C1. (verified)
2. **Empty tarball `skills/` dir** → `enumerate_skills` yields 0-length array, `die "no skills found in tarball"` fires. (verified, good)
3. **Multiple top-level dirs in tarball** → `head -1` picks filesystem-order first, not deterministic. Currently non-issue because GH serves exactly one. (verified today, fragile)
4. **`rm -rf` on symlinked `$dst`** → removes the symlink only, does NOT traverse into the victim dir. Safe. (verified)
5. **Skill dir contains tarball-sourced symlinks** → `cp -R` dereferences; see M3.
6. **Hidden dirs under `skills/`** → globbed `*/` skips them. (verified)
7. **Mid-loop `die`** → partial install state; see M1.

## Spec Compliance

| Spec item | Status |
|---|---|
| `install-skill.sh` (no args) installs all | ✅ |
| Named skills install, fail fast on missing | ✅ |
| `--dry-run` | ✅ |
| `--help`/`-h` | ✅ |
| Requires `~/.openclaw/` | ✅ |
| `rm -rf` + `cp -R` overwrite | ✅ |
| Bash 3.2 compatible | ✅ (empirically confirmed) |
| `set -euo pipefail`, `IFS=$'\n\t'` | ✅ |
| `curl | bash` compatible | ✅ (no stdin reads) |
| `mktemp` + trap cleanup | ✅ |
| Require `SKILL.md` at skill root | ✅ (but see M1 fail-fast concern) |

No deviations from spec. Gaps called out above are **beyond** what the spec demanded, surfaced by the threat model of a `curl | bash` installer.

## Positive Observations

- TLS hardening (`--proto '=https' --tlsv1.2`) matches `install.sh` — good consistency.
- `--max-time 60` prevents indefinite hang on stalled connections.
- `mktemp -d 2>/dev/null || mktemp -d -t openclaw-skill` fallback handles both GNU and BSD mktemp.
- `[ -f "$src/SKILL.md" ]` validation per OpenClaw skill spec — catches corrupt tarballs.
- `printf '[tag] ...' >&2` pattern keeps stdout clean for potential future piping.
- `SKILL.md` path is validated against the *source* (tarball) not the destination — TOCTOU-resistant.
- `parse_args` supports `--` terminator for skills whose names might start with `-`. Nice touch.
- Usage text explicitly calls out the "overwrites existing" behavior — reduces support tickets.

## Recommended Actions (prioritized)

1. **[C1]** Add skill-name validator before any `rm -rf`/`cp -R`. ~5 lines.
2. **[M3]** Add `find -type l` guard on `$src` and/or use `cp -RP`. ~3 lines.
3. **[M2]** Tighten tarball-root detection (name filter or count assertion). ~2 lines.
4. **[M1]** Decide: continue-on-error vs fail-fast for multi-skill installs, document the choice.
5. **[m2]** Extend trap to `INT TERM HUP`. 1 line.

## Metrics

- LOC: 149
- Shellcheck: not executed here; spec claims clean. Recommend running `shellcheck install-skill.sh` in CI (see Phase 3).
- Bash 3.2 compatibility: verified empirically.
- Test coverage: manual smoke tests per Todo list; no automated test harness (Phase 3 scope).

## Unresolved Questions

- Should multi-skill install be atomic (all-or-nothing rollback) or best-effort (install what works, report the rest)? Spec doesn't say; current impl is "fail-fast after partial install," which is the worst of both. Recommend picking one deliberately.
- Long-term: should the installer verify a checksum/signature of the tarball? Today TLS + GitHub trust is the only integrity bar; a `.sha256` alongside tagged releases would harden against repo compromise. Out of scope for phase 2 but worth capturing.
