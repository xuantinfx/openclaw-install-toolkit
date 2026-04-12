# Code Review — Phase 3 (CI Coverage for install-skill.sh)

**Commit:** `f4e40c6`
**Files:** `.github/workflows/ci.yml`, `install-skill.sh`
**Reviewer:** code-reviewer
**Date:** 2026-04-13
**Verdict:** Ship-ready with one real spec drift (shellcheck miss) + one minor hardening suggestion. CI green on both runners is genuine signal.

---

## Scope

- CI workflow additions for `install-skill.sh` smoke test (matrix: ubuntu-latest + macos-latest).
- New `TOOLKIT_ALLOW_INSECURE` env var in `install-skill.sh` to relax curl `--proto` for CI file:// fixtures.
- LOC touched: ~45 (ci.yml) + ~5 (install-skill.sh).

## Overall Assessment

Clean, focused change. The `HOME` override approach is the right call (simpler than adding a second `OPENCLAW_HOME_OVERRIDE`-style flag to install-skill.sh, and the spec justifies this decision). Fixture layout correctly mirrors the real GitHub archive shape. Idempotency + dry-run are both covered. Naming `TOOLKIT_ALLOW_INSECURE` signals danger well. But there's one real drift from the spec and a couple of worthwhile gaps.

---

## Critical

None.

## Major

### M1. Spec drift — `install-skill.sh` is not being shellchecked
- **File:** `.github/workflows/ci.yml:27`
- **Issue:** Phase 3 spec Implementation Step 1 says "After existing `Shellcheck` step, add: `shellcheck install-skill.sh`" and the phase-03 todo list checks off "Add shellcheck step for install-skill.sh (also covers scripts/sync-skill.sh)". The CI only runs `shellcheck install.sh`. Neither `install-skill.sh` nor `scripts/sync-skill.sh` is linted.
- **Impact:** Loss of a cheap static gate on the very script this phase is supposed to harden. Future PRs can land SC2086/SC2155/SC2046-class bugs silently.
- **Fix:**
  ```yaml
  - name: Shellcheck
    run: shellcheck install.sh install-skill.sh scripts/sync-skill.sh
  ```
  (One line change. Fail loud if `sync-skill.sh` path differs.)

## Minor

### m1. `TOOLKIT_ALLOW_INSECURE` is broader than it needs to be
- **File:** `install-skill.sh:99-102`
- **Shape today:** flag flips protos to `=http,https,file`. Only `file` is actually needed for the CI path this phase added.
- **Accidental-prod-trip risk:** low but nonzero. A user copy-pasting a debug command from an issue could set this, and then a compromised DNS resolving the GitHub host could downgrade to plain HTTP and serve a malicious tarball. The current name ("INSECURE") and doc comment mitigate this reasonably well.
- **Safer shape (no over-engineering):** drop `http` from the allowlist — `=https,file` covers every legitimate use case (file:// fixtures in CI, plus the normal HTTPS path). `http` was never required for Phase 3's goal.
  ```bash
  curl_protos='=https,file'
  ```
  This is a one-word change that shrinks the attack surface without complicating the knob. Auto-detecting "only relax when URL starts with `file://`" is tempting but adds parsing logic for marginal benefit — not worth it.
- **Recommendation:** Drop `http`. Keep the env-var shape.

### m2. No assertion that the bogus-skill or symlink-rejection paths fail
- **File:** `.github/workflows/ci.yml:48-86`
- **Issue:** The smoke tests the happy path (install + idempotent + dry-run). It does not assert that `./install-skill.sh nonexistent-skill` exits non-zero, nor that a tarball containing a symlink is rejected. Both are defensive behaviors added in Phase 2 that can regress silently.
- **Low-effort add (<10 lines):**
  ```bash
  # Negative: unknown skill must fail
  if HOME="$home_override" \
       TOOLKIT_TARBALL_URL="file://$fixture_root/toolkit.tar.gz" \
       TOOLKIT_ALLOW_INSECURE=1 \
       ./install-skill.sh bogus-skill-xyz; then
    echo "expected failure for unknown skill"; exit 1
  fi

  # Negative: symlink in tarball must be rejected
  evil_root="$(mktemp -d)"
  evil_stage="$evil_root/openclaw-install-toolkit-main"
  mkdir -p "$evil_stage/skills/evil"
  echo "# x" > "$evil_stage/skills/evil/SKILL.md"
  ln -s /etc/passwd "$evil_stage/skills/evil/leak"
  tar -czf "$evil_root/evil.tar.gz" -C "$evil_root" openclaw-install-toolkit-main
  if HOME="$(mktemp -d)/.openclaw-parent" \
       TOOLKIT_TARBALL_URL="file://$evil_root/evil.tar.gz" \
       TOOLKIT_ALLOW_INSECURE=1 \
       ./install-skill.sh evil 2>/dev/null; then
    echo "expected failure on symlinked tarball"; exit 1
  fi
  ```
  Worth closing now, not deferring — Phase 4 is release. Defensive checks regress silently and this is the last easy opportunity.
- **Caveat on the symlink test:** the stanza above needs an `HOME` pointing at a dir that contains `.openclaw/` (preflight check at `install-skill.sh:90-91`). Reuse the existing `home_override` to avoid that setup dance.

### m3. Silent fixture build failures
- **File:** `.github/workflows/ci.yml:54-57`
- **Issue:** `set -euo pipefail` is set at the top of the step (line 50). `mkdir -p` + `echo` + `tar` all fail loud under `-e`. Good. BUT: if someone later changes `echo "# Test Fixture Skill" > ...` to a multi-line heredoc or command substitution that silently produces an empty file, only the grep assertion at line 70 (`grep -q "Test Fixture Skill"`) would catch it. That's acceptable coverage — noting for awareness only, no action needed.

### m4. `test ! -e` dry-run assertion is slightly narrow
- **File:** `.github/workflows/ci.yml:85`
- **Issue:** `test ! -e "$dry_home/.openclaw/skills/test-fixture"` asserts the skill dir doesn't exist. But if dry-run accidentally created `$dry_home/.openclaw/skills/` (the parent, via `mkdir -p`), this test passes despite a bug. Current `install_one` returns before the `mkdir -p "$OPENCLAW_HOME/skills"` on dry-run, so this isn't a live bug, but a stricter assertion is cheap:
  ```bash
  test ! -e "$dry_home/.openclaw/skills" \
    || { echo "--dry-run created skills/ dir"; exit 1; }
  ```
- **Priority:** low. Defer or close alongside m2.

---

## Honest Trade-off: `TOOLKIT_ALLOW_INSECURE` Design

Asked to be honest on this — the current shape is **fine**. Reasoning:

- **Global flip is acceptable** because (a) the env-var name loudly signals "danger", (b) the help text explicitly says "CI-only... never in production", (c) you'd have to deliberately set it.
- **Scoping to file-only** (`=https,file` instead of `=http,https,file`) is a free improvement — recommend it (m1). Keeps the explicit knob, removes the unused `http` vector.
- **Runtime auto-detection** ("only relax when URL is `file://`") is over-engineering: it adds URL parsing, has a failure mode if the parse is wrong, and doesn't meaningfully reduce surface compared to dropping `http`. **Don't do this.**
- **Alternative design — `TOOLKIT_TARBALL_URL_ALLOW_FILE=1`** (single-purpose flag): marginally better naming but same risk profile. Not worth the rename churn.

Net: keep the env-var shape, drop `http` from the allowlist. Done.

---

## HOME Sandbox Trace (as requested)

Traced `$HOME` / `~` usage in `install-skill.sh`:

1. **Line 17:** `OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"` — resolved at script-load time, AFTER env inheritance from parent shell. Setting `HOME="$home_override" ./install-skill.sh` makes the child process's `$HOME` = override. ✅
2. **Line 90-91:** `[ -d "$OPENCLAW_HOME" ]` preflight. Uses the already-computed `$OPENCLAW_HOME`. ✅
3. **Lines 140, 151, 153, 172:** all go through `$OPENCLAW_HOME`. ✅
4. **Comments/help text only:** lines 3, 11, 35, 39, 43, 48, 49 reference `~/.openclaw` — all inside `printf`/heredocs, never evaluated. ✅
5. **No `eval`, no `~` in executable paths.** ✅

**Verdict:** sandbox is clean. `HOME` override is the correct mechanism and nothing leaks to the runner's real `$HOME`. The CI step's `mkdir -p "$home_override/.openclaw"` correctly pre-creates the dir preflight expects.

One nit: preflight requires `$OPENCLAW_HOME` to exist but doesn't require it to be owned by the user. Not a Phase 3 concern — flagging for future hardening if ever relevant.

---

## Portability Check

- **`tar -czf ... -C $dir $name`**: supported by both GNU tar and macOS bsdtar. ✅
- **`mktemp -d`**: supported on both. The script uses the fallback pattern `mktemp -d 2>/dev/null || mktemp -d -t openclaw-skill` inside `install-skill.sh` (line 95), but CI uses plain `mktemp -d` which is fine for runner environments.
- **`find ... | wc -l | tr -d ' '`**: handles macOS `wc` right-padding. ✅
- **`stat` differences** are in a different step (the existing `install.sh` smoke). Not used in the Phase 3 step. ✅
- **`test -f`, `test ! -e`, `grep -q`**: POSIX. ✅

No portability issues in the Phase 3 step.

---

## Fixture Realism

Against real GitHub archive layout (`https://github.com/.../archive/refs/heads/main.tar.gz`):

| Property | Real archive | Fixture | Match |
|---|---|---|---|
| Single top-level dir | `openclaw-install-toolkit-main/` | `openclaw-install-toolkit-main/` | ✅ |
| `skills/<name>/SKILL.md` at root | yes | yes | ✅ |
| No symlinks | true for this repo | true | ✅ |
| Other sibling files (README, etc.) | yes | no | ⚠️ minor |
| Multiple skills | yes | only one (`test-fixture`) | ⚠️ minor |

The last two are minor — fixture tests the "install one named skill" path well, but doesn't cover the "install all skills" (no-args) path, which is a distinct code branch (`enumerate_skills` loop at `install-skill.sh:125-132`). Adding a second fixture skill + one no-args invocation would close this gap in ~5 lines. Low priority; good fit to fold in with m2.

---

## GitHub Actions Security

- No `${{ github.* }}` or `${{ inputs.* }}` interpolation inside any `run:` block in the new step. ✅
- No `pull_request_target`; workflow uses `pull_request`, which runs with forked-repo token permissions — safe. ✅
- No `actions/checkout@v4` with `persist-credentials: false` needed here since we don't push. ✅
- No shell injection surface in the new step. ✅

Clean.

---

## Spec Adherence (phase-03-ci-coverage.md)

| Spec item | Delivered | Notes |
|---|---|---|
| Extend matrix to both OSs | ✅ | Job already matrix, step inherits |
| `shellcheck install-skill.sh` | ❌ | **M1 — claimed done in todo list but absent in CI** |
| Fixture tarball w/ `openclaw-install-toolkit-main/` root | ✅ | Built fresh, not via `git archive` (correct per spec key insight) |
| `TOOLKIT_TARBALL_URL` override + `file://` | ✅ | |
| `HOME` override (not `OPENCLAW_HOME_OVERRIDE`) | ✅ | Decision matches spec line 59 |
| Assert installed file exists | ✅ | |
| Idempotent re-run | ✅ Bonus, not in spec but good |
| `--dry-run` coverage | ✅ Bonus, not in spec but good |
| Green on both runners | ✅ | Run 24312295304 |
| `<1 min` added CI time | ✅ | (not measured in review, but fixture build + curl file + tar is <10s) |

**Only drift:** M1 (shellcheck).

---

## Coverage Gaps vs Phase 4 Release Readiness

Ranked by how much I'd care before cutting a release:

1. **Shellcheck on install-skill.sh (M1)** — close before release. One-line change, prevents regressions in the script users copy-paste from a `curl | bash` invocation.
2. **Negative-path assertions (m2)** — close before release. Symlink rejection is a security feature; if it regresses silently and we ship, a compromised upstream becomes a cross-user foothold. <10 lines.
3. **Multi-skill / no-args path coverage** — nice-to-have; defer. Low risk of regression in that code branch.
4. **Stricter dry-run assertion (m4)** — defer. Current test passes for the real-world bug it'd catch.

My recommendation: **fix M1 + m2 as one small follow-up PR before Phase 4**, ship everything else as-is.

---

## Positive Observations

- `TOOLKIT_ALLOW_INSECURE` naming: loud, specific, self-documenting. Future-me thanks you.
- Fixture layout matches the production archive shape exactly — this is the kind of detail that separates a smoke test from a green-light-that-proves-nothing.
- Idempotency re-run is a genuine value-add over the spec's minimum.
- `--dry-run` assertion using a *separate* `$HOME` is the right isolation — avoids false positives from the prior install.
- Comments in the CI step explain the intent (the fixture layout comment is a gift to future maintainers).
- `set -euo pipefail` at the top of the step catches silent-failure footguns in the fixture build.

---

## Recommended Actions

1. **[Major]** Add `install-skill.sh` (and `scripts/sync-skill.sh` if that path exists) to the `Shellcheck` step. One-line fix. Matches spec.
2. **[Minor]** Drop `http` from `TOOLKIT_ALLOW_INSECURE` proto allowlist — use `=https,file`.
3. **[Minor]** Add negative-path assertions to the smoke (unknown skill must fail, symlinked tarball must fail). ~15 lines.
4. **[Optional]** Add a second fixture skill and one no-args invocation to cover `enumerate_skills`.
5. **[Optional]** Tighten dry-run assertion to `test ! -e "$dry_home/.openclaw/skills"`.

None of these block merge of the current commit. M1 + m2 are worth closing as a small follow-up PR before cutting the Phase 4 release.

---

## Metrics

- Lint issues (in Phase 3 additions): 0
- Spec drift: 1 (M1)
- Critical: 0 / Major: 1 / Minor: 4
- Security-relevant gaps: 1 (symlink-path coverage, m2)

## Unresolved Questions

- Does `scripts/sync-skill.sh` exist and need shellchecking too? Todo list claims so; I didn't verify the file is committed — worth a quick `ls scripts/` before writing the one-line shellcheck fix.
- Is the Phase 4 release cutting from `main` or a release branch? If release branch, M1+m2 must land there too.
