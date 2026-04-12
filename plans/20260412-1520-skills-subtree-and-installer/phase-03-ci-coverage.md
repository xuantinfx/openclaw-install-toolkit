# Phase 3 — CI Coverage + Dry-Run Smoke

## Overview
- **Priority:** P1
- **Status:** completed (2026-04-13)
- **Depends on:** phase-02

Extend existing `.github/workflows/ci.yml` to shellcheck `install-skill.sh` and run a dry-run smoke against a fixture skill, on both macOS and Ubuntu.

## Key Insights

- CI can't fetch from the live tarball URL (chicken-and-egg: PR branch isn't in `main.tar.gz` yet). Use `TOOLKIT_TARBALL_URL` env override pointing at a local fixture tarball built from the checkout.
- `git archive HEAD --format=tar.gz` builds a tarball of the current commit — perfect for CI.
- Serve it via `file://` URL? `curl` supports `file://`. Simpler than a temp HTTP server.
- Need a fixture skill to exist in the tarball. For CI-only paths, write `skills/test-fixture/SKILL.md` at runtime before archiving — don't commit a test fixture.

## Requirements

### Functional
- CI job matrix already covers `{ubuntu-latest, macos-latest}` — extend both.
- New step: `shellcheck install-skill.sh`.
- New step: dry-run smoke:
  - Create ephemeral `skills/test-fixture/SKILL.md` with dummy content.
  - `git archive HEAD` → `/tmp/toolkit.tar.gz` (INCLUDING the ephemeral file — use `tar -czf` directly on the workspace instead of `git archive` which only sees committed files).
  - Run `OPENCLAW_HOME_OVERRIDE="$(mktemp -d)" mkdir "$OPENCLAW_HOME_OVERRIDE" && TOOLKIT_TARBALL_URL="file:///tmp/toolkit.tar.gz" ./install-skill.sh test-fixture`
  - Assert `$OPENCLAW_HOME_OVERRIDE/skills/test-fixture/SKILL.md` exists (or `~/.openclaw/skills/test-fixture/SKILL.md` if we don't support OPENCLAW_HOME_OVERRIDE in install-skill.sh).

### Non-functional
- Zero shellcheck warnings on `install-skill.sh`.
- Both runners green.
- Total added CI time <1 minute.

## Architecture

```yaml
# .github/workflows/ci.yml (additions)
- name: Shellcheck install-skill.sh
  run: shellcheck install-skill.sh

- name: Build fixture tarball
  run: |
    mkdir -p skills/test-fixture
    echo "# Test Fixture" > skills/test-fixture/SKILL.md
    # tarball mimics github archive format: top-level dir = repo-branch
    mkdir -p /tmp/stage/openclaw-install-toolkit-main
    cp -R . /tmp/stage/openclaw-install-toolkit-main/
    tar -czf /tmp/toolkit.tar.gz -C /tmp/stage openclaw-install-toolkit-main

- name: Install-skill smoke
  run: |
    export HOME_OVERRIDE=$(mktemp -d)
    mkdir -p "$HOME_OVERRIDE/.openclaw"
    # install-skill.sh reads $HOME for ~/.openclaw — we override HOME
    HOME="$HOME_OVERRIDE" TOOLKIT_TARBALL_URL="file:///tmp/toolkit.tar.gz" \
      ./install-skill.sh test-fixture
    test -f "$HOME_OVERRIDE/.openclaw/skills/test-fixture/SKILL.md"
```

Decision: **override `HOME` rather than adding `OPENCLAW_HOME_OVERRIDE` to install-skill.sh** — simpler, one less special-cased env var, and the existing install.sh's OPENCLAW_HOME_OVERRIDE is for dry-run mode only. For install-skill.sh, `~/.openclaw` resolves from `$HOME` — just override that in tests.

## Related Code Files

### Modify
- `.github/workflows/ci.yml`

## Implementation Steps

1. After existing `Shellcheck` step, add: `shellcheck install-skill.sh`.
2. Add "Build fixture tarball" step:
   - `mkdir -p skills/test-fixture && echo "# Test Fixture" > skills/test-fixture/SKILL.md`
   - Build tarball with `openclaw-install-toolkit-main/` as the top-level dir (matching real GitHub archive format).
3. Add "Install-skill smoke" step:
   - Override `HOME` → mktemp dir.
   - Override `TOOLKIT_TARBALL_URL` → `file:///tmp/toolkit.tar.gz`.
   - Run `./install-skill.sh test-fixture`.
   - Assert `$HOME/.openclaw/skills/test-fixture/SKILL.md` exists.
4. Verify step runs green on both runners (push PR, watch matrix).

## Todo List
- [x] Add shellcheck step for install-skill.sh (also covers scripts/sync-skill.sh)
- [x] Add fixture tarball build step
- [x] Add install-skill smoke step with assertions (install + idempotent re-run + dry-run)
- [x] Verify green on both runners (run 24312295304 — ubuntu + macos both success)

## Success Criteria
- CI green on both runners.
- Shellcheck passes with zero warnings.
- Smoke step confirms end-to-end fetch → extract → copy on both OSs.

## Risk Assessment
- **`curl file://`** on some minimal Linux images may not be enabled. GH Actions ubuntu-latest + macos-latest both have full curl builds. Verified.
- **Tarball format differences**: macOS bsdtar vs GNU tar may differ in `-czf`. Both support the flags we use.
- **HOME override surprises**: install-skill.sh must read `~/.openclaw` via `$HOME` expansion, not hardcoded path. Code review check.

## Security
- No secrets in CI for this feature.
- `file://` URL is local to the runner — no exposure.

## Next Steps
→ Phase 4 (README + release).
