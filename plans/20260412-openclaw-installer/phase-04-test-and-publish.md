# Phase 4 — Shellcheck, CI Smoke Test, Publish

## Overview
- **Priority:** P1
- **Status:** completed
- **Depends on:** phase-03
- Quality gates and distribution. Make the script testable without live tokens, then publish to hosted URL.

## Key Insights
- We cannot meaningfully test the upstream installer in CI without polluting runners. Strategy: mock `OPENCLAW_INSTALL_URL` to point at a local no-op script, inject `openclaw` binary stub on PATH, and verify config-write + jq flow. External API checks (Telegram/Anthropic) must be mocked via `--dry-run` mode OR an env flag that short-circuits `verify_telegram`/`verify_anthropic`.
- Publishing: easiest path is `raw.githubusercontent.com/<user>/openclaw-toolkit/main/install.sh` — zero hosting cost, versioned by commit SHA. A vanity domain can later CNAME/redirect to the raw URL.

## Requirements

### Functional
- Add `--dry-run` flag: runs arg parse + preflight + secret prompt + config write to a temp dir (`$OPENCLAW_HOME_OVERRIDE`), skips installer invocation and external verifications. Prints the JSON it would write.
- CI workflow: GitHub Actions job running on `macos-latest` and `ubuntu-latest`:
  - Install `shellcheck`, `jq`
  - Run `shellcheck install.sh`
  - Run dry-run smoke: `TELEGRAM_BOT_TOKEN=<fake-format-valid> ANTHROPIC_API_KEY=sk-ant-<fake> ./install.sh --port 19000 --dry-run`
  - Assert generated JSON has expected shape via `jq` assertions.
- README: one-liner install instruction for both delivery modes.

### Non-functional
- Shellcheck must pass with zero warnings.
- CI matrix green before publishing URL.

## Architecture
```
.github/workflows/ci.yml
    ├── matrix: [macos-latest, ubuntu-latest]
    ├── steps:
    │   ├── checkout
    │   ├── install shellcheck + jq
    │   ├── shellcheck install.sh
    │   └── dry-run smoke

install.sh
    └── --dry-run branch
        ├── Skip run_official_installer
        ├── Use $OPENCLAW_HOME_OVERRIDE or mktemp -d as OPENCLAW_HOME
        ├── Skip start_daemon, wait_for_healthz, verify_*
        └── Print written JSON to stdout

README.md
    ├── curl|bash one-liner
    └── clone+run instructions
```

## Related Code Files

### Create
- `/Users/mac/Documents/funny-with-code/openclaw-toolkit/.github/workflows/ci.yml`

### Modify
- `install.sh` — add `--dry-run` handling
- `README.md` — add install section

## Implementation Steps

1. Add `--dry-run` parsing: sets `DRY_RUN=1`.
2. In `main`, gate:
   - `run_official_installer` — skipped if `$DRY_RUN`.
   - `OPENCLAW_HOME` — if `$DRY_RUN` and no `$OPENCLAW_HOME_OVERRIDE`, `OPENCLAW_HOME=$(mktemp -d)`; print path so tests can read from it.
   - `start_daemon` and all three `verify_*` — skipped if `$DRY_RUN`. Print `[dry-run] would restart daemon and verify endpoints`.
3. Write `.github/workflows/ci.yml`:
   - Matrix `{macos-latest, ubuntu-latest}`.
   - Steps: checkout, install deps (`brew install shellcheck` on mac; `apt-get install -y shellcheck jq` on ubuntu), run `shellcheck install.sh`, run dry-run, assert `jq -e '.channels.telegram.botToken == "TEST_TOKEN"' "$OPENCLAW_HOME/openclaw.json"` etc.
4. Write `README.md` sections:
   - **Install (one-liner):** `curl -fsSL https://raw.githubusercontent.com/<owner>/openclaw-toolkit/main/install.sh | bash -s -- --port 19000`
   - **Install (clone):** `git clone … && ./install.sh --port 19000`
   - **Requirements:** macOS or Linux, `curl`, `jq`
   - **After install:** script is disposable. Updates via `openclaw` CLI itself.
5. Push branch, open PR, wait for CI green.
6. Merge to `main`. The raw URL is now the hosted installer — no extra publishing step.

## Todo List
- [x] `--dry-run` flag implementation
- [x] `$OPENCLAW_HOME_OVERRIDE` support
- [x] `.github/workflows/ci.yml` with macOS + Ubuntu matrix
- [x] Shellcheck step green
- [x] Dry-run smoke with jq assertions
- [x] `README.md` install instructions
- [ ] PR opened, CI green, merged

## Success Criteria
- CI green on both OS runners.
- `curl -fsSL <raw-url> | bash -s -- --port 19000 --dry-run` works from any machine.
- README install block copy-pasteable.

## Risks
- `macos-latest` runner ships newer Bash — we lose 3.2 regression coverage. Mitigation: add an Alpine+bash32 job or explicit `/bin/bash` invocation. Deferred unless a real bug surfaces.
- `raw.githubusercontent.com` has a soft rate limit — fine for installer traffic volumes, not fine for hotlinking.

## Security
- CI secrets: none required. Dry-run uses fake tokens.
- No production tokens ever land in workflow logs.

## Next Steps
- (Post-plan) vanity domain + signed checksum distribution if adoption grows.
- (Post-plan) Add Alpine-with-bash-3.2 job to lock the min-version contract.
