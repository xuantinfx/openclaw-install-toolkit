# env-risk: post-fix review of install.sh (HEAD ee649af)

Re-review after commits `c245f77`, `97845b5`, `ee649af` landed. Prior report:
`plans/reports/env-risk-260421-1121-fresh-device-install.md`.

## 1. Prior-finding status

| ID | Fix shipped | Verdict |
|---|---|---|
| L1 jq missing on <Sequoia | `bootstrap_jq_if_missing` (install.sh:162) auto-downloads jq-1.7.1 into `$OPENCLAW_HOME/bin`, then preflight re-checks with `jq --version` (line 231) | LANDED |
| L2 `brew install jq` hint dead-ends | preflight hint now says "auto-download failed. Install manually: Homebrew…OR jqlang.org/download" (line 218). Only shown if bootstrap also fails | LANDED |
| L3 `$SHELL` wrong source of truth | Multi-rc writer (line 704) touches `.zshrc` (always) + `.bash_profile`/`.bashrc` (only if pre-existing) + fish/nu hint block | LANDED |
| L4 Quarantine / install.command UX | instruction.txt STEP 2 rewritten: Way A (drag-to-Terminal) is RECOMMENDED with an explicit banner, Way B is the fallback with the right-click-Open walkthrough inline | LANDED |

All four are genuine fixes — not papered over.

## 2. New risks introduced by the fixes

**N1 (MEDIUM) — jq download is unverified.** No SHA256 / signature check on
`bootstrap_jq_if_missing` (line 186). Threat model: TLS MITM on corporate proxy
with a rogue root CA, or jqlang release-pipeline compromise. Impact is real —
the binary goes straight onto the user's `$PATH` and is then executed by
`backup_and_write_config` (line 534) handling plaintext secrets. jqlang does
publish `sha256sum.txt` alongside each release; pinning those hashes alongside
`JQ_VERSION` is a one-liner that removes the supply-chain surface. Recommend
fix.

**N2 (LOW) — Bootstrap fails on air-gapped / GitHub-blocked networks.** URL is
hardcoded to `github.com/jqlang/jq/releases/download/...`. Corporate networks
that proxy-block github.com (not unheard of) → bootstrap fails → user falls
through to the improved hint. Hint is actionable, so acceptable per YAGNI.
Could add `OPENCLAW_JQ_URL` env override for completeness, but defer.

**N3 (LOW) — `mkdir -p "$OPENCLAW_HOME/bin"` runs at preflight, before the
git-worktree check (line 237).** On a box where `$OPENCLAW_HOME` sits inside a
git repo, we create `bin/` then `die` three lines later — leaves a stray empty
dir. Cosmetic, not a security or correctness issue. Swap order if trivial
(cheap fix: run the worktree probe first in `preflight`); otherwise defer.

**N4 (LOW) — `.zshrc` spuriously created for fish/nu-only users.** Multi-rc
write (line 712) creates `.zshrc` unconditionally. Opt-out exists
(`OPENCLAW_NO_RC_EDIT=1`) but is under-advertised — not in instruction.txt,
only in `--help`. Fish/nu users ALSO get a print-manual-hint block (line 729),
but the zshrc file is still created. Either document the opt-out in
instruction.txt, or skip `.zshrc` creation when `$SHELL` ends in
`fish`/`nu`/`nushell`. Defer; small cohort.

**N5 (LOW) — Reinstall with different `OPENCLAW_HOME` appends a second line.**
`grep -qxF "$line"` (line 715) is exact-match. If user reinstalls with a
different override, they get two `export PATH=…` lines. Last one wins at
source-time, so functionally benign; cosmetic only. Comment in the code would
help future maintainers; no action needed now.

**N6 (LOW) — Any jq passes the functional check, including ancient <1.5.** Line
231 only runs `jq --version`. jq 1.4 predates `--argjson` (used line 535) and
would fail inside `backup_and_write_config` with "jq: Unknown option:
--argjson". Realistically jq <1.5 is extinct on supported targets (1.5 shipped
2015); keep deferred.

**Verified safe:** `set -euo pipefail` + `if ! jq --version >/dev/null 2>&1`
pattern at line 231 is correct — negated check of a pipeline whose rc is the
last cmd, wrapped in `if`, is exempted from `-e`. No silent exit.

## 3. Remaining POSSIBLE findings (from prior report)

| ID | Recommendation |
|---|---|
| P1 `npm` without `require_cmd` | **Retire.** `|| true` fully absorbs the error; upstream install-cli.sh is npm-based so any real missing-npm surfaces there with its own hint. Not our problem to catch twice. |
| P3 locale grep edge cases | **Retire.** Token formats are ASCII-only by spec; `LC_ALL=C` would be belt-and-suspenders with no real payoff. |
| P4 `$OPENCLAW_HOME` with spaces/unicode | **Keep deferred.** Exotic override + cosmetic only. Functionality verified correct; no user reports. |
| P5 manual `openclaw dashboard` after opt-out | **Partially fixed** — `on_success` (line 777) tells every user "Re-open any time with: openclaw dashboard" regardless of opt-out. Good enough. |
| P6 `/dev/tcp` on custom bash | **Keep deferred.** Custom-bash users are technical enough to self-diagnose. |

## 4. instruction.txt readability

The Way A / Way B rewrite is clear. The ">>> Not sure which to pick? Use Way
A <<<" banner is exactly what a non-technical reader needs. One nit: STEP 2
says "You received a file called openclaw-toolkit.zip via message" — a user
who got it via AirDrop/email may briefly hesitate. Defer; too small to churn
docs for.

## Unresolved questions

1. **Pin jq SHA256?** jqlang publishes `sha256sum.txt` per release. Adding a
   4-entry table keyed by `asset_name` is ~15 lines and closes N1. Worth it
   before wider distribution?
2. **Swap order of `mkdir bin/` and git-worktree probe** to kill N3, or is a
   stray empty dir on a refused install acceptable?
3. **Mention `OPENCLAW_NO_RC_EDIT=1` in instruction.txt** for dotfile-managed
   / chezmoi / nix-home users, or keep it a power-user-only env var?

---

**Status:** DONE
**Summary:** All four LIKELY findings from the prior review landed as genuine
fixes (not workarounds). One new MEDIUM risk introduced: unverified jq
download (N1 — supply-chain surface, recommend SHA256 pinning). Five new LOW
items catalogued, all deferrable under YAGNI. Of the six prior POSSIBLEs, two
should be retired outright, three kept deferred, one partially addressed.
**Concerns/Blockers:** None — review only. N1 is the only item worth a
pre-distribution follow-up.
