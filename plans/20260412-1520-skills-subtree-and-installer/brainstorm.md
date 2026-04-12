---
status: brainstorm-complete
created: 2026-04-12
scope: skill-distribution-via-subtree
---

# Skills Sub-Git + Customer Installer — Brainstorm Summary

Deliver private-source Skills (starting with `hoangnhatfe/content-monitor`) to customer OpenClaw installs via a publicly-distributed `install-skill.sh`. Weekly update cadence. Pinned to toolkit commit. Designed for multiple future skills.

## Problem

- Want a "sub-git" linkage so `content-monitor` stays editable in its own repo but ships through this toolkit.
- `content-monitor` source is private (edit-only); distributing the skill files via customer installer is fine.
- Customers land files at `~/.openclaw/skills/<name>/` (per OpenClaw docs — gateway auto-watches).
- Must work under `curl | bash` delivery (no submodule, no authed fetch on customer side).

## Locked decisions

| Aspect | Choice | Why |
|---|---|---|
| Sub-git mechanism | **Git subtree** under `skills/<name>/` | Files are in the toolkit repo → tarball / raw fetch just works. No submodule recursion, no customer auth. |
| Sync cadence | **Manual weekly** `git subtree pull --squash` | User chose control over automation. Re-assess if cadence becomes painful. |
| Customer installer | **Separate `install-skill.sh`** | Decouples skills from gateway install; customers can refresh skills without reinstalling the gateway. |
| Skill count | **Multi-skill from day one** | User expects more skills; glob `skills/*/` generically. Marginal complexity, meaningful future-proofing. |
| Pinning | **Toolkit commit = skill version** | Customer pulls tarball of `main`; whatever is committed = what ships. No separate version channel. |

## Ruled out

- **Submodule** — tarball + `curl|bash` don't fetch submodule content; customers get empty dir. Fatal.
- **Runtime clone of content-monitor** — requires customer auth to private repo. Fatal.
- **CI auto-sync** — user preferred manual for now. Revisit if weekly discipline slips.
- **Runtime fetch from content-monitor release tarball** — overkill given subtree already bundles files.

## Recommended architecture

```
openclaw-install-toolkit/            (public)
├── install.sh                        (gateway installer — existing)
├── install-skill.sh                  (NEW — skill installer for customers)
├── scripts/
│   └── sync-skill.sh                 (OPTIONAL — maintainer helper around subtree)
├── skills/
│   └── content-monitor/              (subtree of hoangnhatfe/content-monitor)
│       └── SKILL.md
└── .github/workflows/ci.yml          (extend to shellcheck new script)
```

### Maintainer flow (you, weekly)

One-time setup:
```bash
git subtree add --prefix=skills/content-monitor \
  git@github.com:hoangnhatfe/content-monitor.git main --squash
git push
```

Weekly refresh:
```bash
git subtree pull --prefix=skills/content-monitor \
  git@github.com:hoangnhatfe/content-monitor.git main --squash
git push
```

Adding a second skill later:
```bash
git subtree add --prefix=skills/<name> <url> main --squash
# install-skill.sh picks it up automatically via skills/* glob
```

Optional `scripts/sync-skill.sh` wrapper:
```bash
./scripts/sync-skill.sh content-monitor          # pulls from known upstream
./scripts/sync-skill.sh --all                    # pull all configured skills
```
A lookup table `scripts/skills.map` maps `<name>` → `<git-url>`.

### Customer flow

Primary one-liner (install all skills):
```bash
curl -fsSL https://raw.githubusercontent.com/xuantinfx/openclaw-install-toolkit/main/install-skill.sh | bash
```

Specific skill(s):
```bash
curl -fsSL https://.../install-skill.sh | bash -s -- content-monitor
```

### `install-skill.sh` behavior

1. Verify `~/.openclaw/` exists → otherwise: `die "run install.sh first"`.
2. Fetch toolkit tarball: `https://github.com/xuantinfx/openclaw-install-toolkit/archive/refs/heads/main.tar.gz` → mktemp dir.
3. Enumerate requested skills (args) OR all `skills/*/` in tarball.
4. For each: `rm -rf ~/.openclaw/skills/<name>` then `cp -R` fresh copy.
5. Print summary: which skills installed + note gateway auto-picks up on next agent turn.
6. Cleanup tmpdir.

Bash 3.2 compatible. `set -euo pipefail`. `shellcheck` clean. `--dry-run` for CI.

### CI update

Extend `.github/workflows/ci.yml`:
- `shellcheck install-skill.sh` on both runners.
- Dry-run smoke: assert the tarball fetch + copy logic works against a fixture skill dir.

## Considerations / risks

- **Leak risk**: content-monitor is edit-private but commits land in PUBLIC toolkit. Anything in content-monitor main = world-readable. Never commit secrets to content-monitor main.
- **Sync discipline**: manual weekly subtree pull WILL slip. If it does more than twice, reconsider CI auto-PR.
- **Forgot-to-push**: subtree pull updates local repo only. Must `git push` immediately after, or customers won't see it.
- **Skill watch**: OpenClaw gateway auto-reloads on next agent turn (default `skills.load.watch: true`). No explicit daemon restart needed after `install-skill.sh`.
- **Permissions on `~/.openclaw/skills/<name>`**: keep default (0755 dirs, 0644 files). No secrets in skill files by policy.
- **Breaking upstream change**: manual subtree pull gives you the chance to eyeball diff before pushing. Actually an advantage over auto-sync here.
- **Tarball size**: toolkit tarball includes plans/ and reports/. As the toolkit grows, customer fetch gets heavier. Mitigation: switch to `git archive` or release-asset tarballs later. Not urgent.

## Success criteria

1. `git subtree pull --prefix=skills/content-monitor ... main --squash` updates the tree with one command; `git push` ships it.
2. Customer runs `curl -fsSL .../install-skill.sh | bash` and ends up with `~/.openclaw/skills/content-monitor/SKILL.md`.
3. Gateway picks up skill within one agent turn (verifiable via `openclaw` CLI or a test query).
4. Adding skill #2 takes one `git subtree add` + no changes to `install-skill.sh`.
5. CI green on both macOS and Ubuntu.

## Next steps

1. Run one-time `git subtree add` for `content-monitor` → verify files land.
2. Implement `install-skill.sh` with multi-skill support + dry-run.
3. Extend CI to shellcheck new script + add tarball-fetch smoke.
4. (Optional) Write `scripts/sync-skill.sh` wrapper + `scripts/skills.map`.
5. Update README with customer install-skill one-liner.
6. Manual end-to-end test: sync → push → customer-side install-skill → verify gateway sees skill.

## Open questions

- Does the user have SSH access to `hoangnhatfe/content-monitor`? (git subtree add will fail otherwise.)
- Should `install-skill.sh` offer a `--ref <sha>` flag for pinned customer installs? YAGNI for now.
- Skill uninstall: out of scope for initial version. Add if needed.
