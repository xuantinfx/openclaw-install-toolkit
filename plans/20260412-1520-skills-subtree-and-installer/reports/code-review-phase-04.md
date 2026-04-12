# Code Review — Phase 4 (README updates)

**File:** `README.md` (commit `02bed85`)
**Reviewer focus:** docs correctness, completeness, security claim accuracy, consistency.
**Manual E2E:** already green (one-liner verbatim, SKILL.md landed, dry-run wrote nothing).

## Summary

README is publishable. Command one-liners are correct (verified against `install-skill.sh` CLI surface), security claims match enforcement code, and `brainstorm.md` link resolves. **Two real gaps** worth fixing before release: the Requirements section misleads skill-only users by listing `jq` as required, and the Environment overrides table omits the two env vars that `install-skill.sh` actually honors (`TOOLKIT_TARBALL_URL`, `TOOLKIT_ALLOW_INSECURE`). Flags table is install.sh-only and would benefit from a note. No critical defects.

---

## Critical
_None._ Every copy-pasteable command is correct.

Verification notes (argument parsing, since this was the primary concern):

- `bash -s -- content-monitor` (line 34): bash consumes the first `--` as its own end-of-options marker, so `content-monitor` reaches the script as `$1`. `parse_args` hits the `*)` case at install-skill.sh:67 and appends it to `SKILLS`. Correct.
- `bash -s -- --dry-run` (line 37): same mechanism — `--dry-run` reaches the script as `$1` and matches the `--dry-run)` case at install-skill.sh:63. Correct.
- `bash` (no args, line 31): installs every skill in tarball via `enumerate_skills` at install-skill.sh:126-136. Correct.
- Security claims on line 85 — each one checks out against the script:
  - "non-identifier skill names" → `validate_skill_name` at install-skill.sh:78-85 (`^[a-z0-9][a-z0-9_-]{0,63}$`).
  - "multi-root tarballs" → top-level dir count assertion at install-skill.sh:117-120 (rejects anything other than exactly 1).
  - "any tarball containing symlinks" → `find ... -type l | read -r` at install-skill.sh:111-113.
  - Phrasing is accurate, no overclaim.

## Major

### M1. Requirements section misleads skill-only users
README lines 58-62 say the toolkit requires `curl, jq`. That's accurate for `install.sh` (which shells out to `jq` for config-building at install.sh:194), but `install-skill.sh` only needs `curl` and `tar` (install-skill.sh:88-89). A user who already has openclaw installed elsewhere and only wants to run `install-skill.sh` will install `jq` unnecessarily, or worse, bounce off the requirement.

**Suggested fix:** split the list, e.g.

```markdown
## Requirements

- macOS or Linux, Bash 3.2+
- `curl`
- `jq` — only for `install.sh` (config builder); not needed for `install-skill.sh`
```

### M2. Env overrides table omits `install-skill.sh` variables
Table on lines 74-79 only lists `install.sh` vars. `install-skill.sh` reads:

- `OPENCLAW_HOME` (install-skill.sh:17) — already in the table but currently reads as install.sh-only.
- `TOOLKIT_TARBALL_URL` (install-skill.sh:19) — **missing**.
- `TOOLKIT_ALLOW_INSECURE` (install-skill.sh:100-104) — **missing**. The security note on line 85 references it by name but a reader scanning the env table won't find it.

**Suggested fix:** add two rows and annotate which script each var applies to, e.g.:

```markdown
| Var | Scope | Purpose |
|---|---|---|
| `TELEGRAM_BOT_TOKEN`    | install.sh       | Skip the token prompt |
| `ANTHROPIC_API_KEY`     | install.sh       | Skip the key prompt |
| `OPENCLAW_INSTALL_URL`  | install.sh       | Override upstream installer URL |
| `OPENCLAW_HOME`         | both             | Override install dir (default `~/.openclaw`) |
| `TOOLKIT_TARBALL_URL`   | install-skill.sh | Override tarball source (default: public main) |
| `TOOLKIT_ALLOW_INSECURE`| install-skill.sh | CI-only: allow http/file URLs (never in prod) |
```

## Minor

### m1. Flags table is install.sh-only; no hint of this
Lines 64-70 list `--port`, `--dry-run`, `--help`. A reader doesn't know whether these apply to `install-skill.sh`. `--dry-run` in particular has two different behaviors: install.sh says "Validate inputs, skip installer + daemon"; install-skill.sh says "fetch + list, no writes." Add a scope column analogous to M2, or a one-liner under the table: "`install-skill.sh` accepts `--dry-run` and `--help`; see `install-skill.sh --help`."

### m2. "OpenClaw handles its own updates" (line 21) has no scope qualifier
The sentence now sits two sections above the new skill flow. A reader could reasonably infer skills also auto-update, which they don't — maintainers must re-run `sync-skill.sh` and customers must re-run `install-skill.sh`. Consider: "OpenClaw handles its own updates. (Skills are refreshed by re-running `install-skill.sh`.)"

### m3. Status blurb is dense
Line 5 crams four facts into one sentence: feature list, subtree mechanism, auto-reload behavior, CI scope. Splitting into two sentences would read better, but this is style preference — not a blocker.

### m4. "curl, jq" on line 62 uses a comma where a bulleted sub-list would be clearer
Trivial; only worth doing if you also fix M1.

### m5. `TOOLKIT_ALLOW_INSECURE` described inline but not in the env table
Called out already under M2. Flagged separately because a reader searching for "ALLOW_INSECURE" hits only the prose, not the reference table.

## Positive observations

- One-liners verbatim-copyable; no `<placeholder>` strings, no shell escapes to unwind.
- Idempotency caveat ("target is replaced wholesale, so don't hand-edit") on line 40-41 is exactly the right warning.
- "Refuses to run if `~/.openclaw/` is missing" (line 41-42) pre-empts the most likely support ticket.
- Security paragraph on line 85 is concise and *accurate* against the script — no overclaiming of what the validators check.
- `brainstorm.md` link resolves (`plans/20260412-1520-skills-subtree-and-installer/brainstorm.md` exists, 6793 bytes).
- Maintainer section correctly warns that `skills/*/` is public; reinforces what phase-01's scripts already enforce.

## Typos / phrasing

- Line 5 status blurb: "Shellcheck + E2E smoke on macOS + Ubuntu for both installers." — reads as a bullet fragment, not a sentence. Acceptable for a status line.
- Line 85: "can't path-traverse into `~/.openclaw/` or smuggle `cp -R` targets" — "smuggle `cp -R` targets" is jargon-y for end-users. Suggest: "or trick `cp -R` into following a symlink out of the tarball."
- No detected AI-bloat phrasing (no "robust", "seamless", "leverages", "empower").

## Recommended action order

1. M1 — 1-line Requirements tweak (prevents user confusion).
2. M2 — env-table additions (docs parity with shipped env surface).
3. m1 — flag-table scope (either add column or one-liner).
4. m2 / m3 / m5 — polish.

Everything above is docs-only. No code changes required.

## Metrics

- Lines reviewed: 89 (README.md).
- Commands verified by re-reading source: 3 (all pass).
- Security claims verified against script: 3 (all match).
- Dead links: 0.

## Unresolved questions

- Does `TOOLKIT_TARBALL_URL` ever want to be a supported customer-facing override, or is it intended purely for CI fixtures? If the latter, document it alongside `TOOLKIT_ALLOW_INSECURE` with the same "CI only" caveat. The script itself has no warning when a non-default URL is used, so README is currently the only place this distinction can land.
- Should the README call out that re-running `install-skill.sh` is how customers get skill updates? Currently only the maintainer section mentions refresh cadence.
