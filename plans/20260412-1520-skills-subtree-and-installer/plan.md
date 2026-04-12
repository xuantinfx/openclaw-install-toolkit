---
status: completed
created: 2026-04-12
completed: 2026-04-13
scope: skill-distribution-via-subtree
---

# Skills Sub-Git + Customer Installer — Implementation Plan

Ship OpenClaw skills to customers via a public `install-skill.sh` that reads from `skills/<name>/` directories bundled into this toolkit via git subtree. First skill: `content-monitor` (private source at `hoangnhatfe/content-monitor`).

## Context Links

- Brainstorm: [./brainstorm.md](./brainstorm.md)
- OpenClaw skills docs (context7): `/openclaw/openclaw`
- Customer-side skill home: `~/.openclaw/skills/<name>/SKILL.md` (gateway auto-watches)
- Existing installer: `../../install.sh`

## Docs-verified facts (context7 `/openclaw/openclaw`)

- **Target path for shared skills:** `~/.openclaw/skills/<name>/SKILL.md` — explicit in FAQ: "For skills shared across multiple agents, store them in `~/.openclaw/skills/<name>/SKILL.md`".
- **Precedence** (high → low): workspace `~/.openclaw/workspace/skills/` > project > personal-agent > managed/local > bundled > `skills.load.extraDirs`.
- **Skill anatomy:** required `SKILL.md` (YAML frontmatter with `name` + `description` + markdown body). Optional dirs: `scripts/` (executables), `references/` (context docs), `assets/` (templates etc.).
- **Auto-reload:** gateway watches the skills tree with `skills.load.watch: true` as the default — no daemon restart needed after `install-skill.sh`.
- **Filesystem check** on this machine confirms `~/.openclaw/skills/` exists and is populated with other skills (`doc-conversion/`, `humanizer/`, symlinks). Our write target is non-conflicting.

## Key Locked Decisions

- Git **subtree** (not submodule) — tarball + `curl|bash` must just work
- **Manual** weekly `git subtree pull --squash` — no CI auto-sync yet
- **Separate** `install-skill.sh` (not bundled into `install.sh`)
- **Multi-skill** design from day one — glob `skills/*/` generically
- Customer fetches toolkit tarball from `https://github.com/xuantinfx/openclaw-install-toolkit/archive/refs/heads/main.tar.gz`
- Bash 3.2 compatible, shellcheck clean, `--dry-run` for CI

## Phases

| # | Phase | Status | File |
|---|---|---|---|
| 1 | Subtree bootstrap + maintainer helper | completed | [phase-01-subtree-bootstrap.md](./phase-01-subtree-bootstrap.md) |
| 2 | `install-skill.sh` — tarball fetch + copy | completed | [phase-02-install-skill-script.md](./phase-02-install-skill-script.md) |
| 3 | CI coverage + dry-run smoke | completed | [phase-03-ci-coverage.md](./phase-03-ci-coverage.md) |
| 4 | README + release | completed | [phase-04-readme-and-release.md](./phase-04-readme-and-release.md) |

## Critical Dependencies

- SSH access to `git@github.com:hoangnhatfe/content-monitor.git` (for subtree add)
- `content-monitor/main` contains a valid `SKILL.md` at its root (or we subtree a subdir)
- Toolkit repo stays public (customer installer depends on unauthenticated tarball fetch)
- `curl`, `tar` on customer machine (both preinstalled on macOS + Linux)

## Success Criteria

1. `skills/content-monitor/SKILL.md` present in toolkit after subtree add + push
2. `curl -fsSL .../install-skill.sh | bash` on a fresh machine deposits `~/.openclaw/skills/content-monitor/SKILL.md`
3. OpenClaw gateway sees the skill on next agent turn (no restart needed)
4. Adding a second skill = `git subtree add --prefix=skills/<name>` only; no script changes
5. CI green on both macOS + Ubuntu for the new script

## Out of Scope (YAGNI)

- CI auto-sync of content-monitor (revisit if manual cadence slips)
- Skill uninstall subcommand
- `--ref <sha>` pinning flag for customers
- Skill signature verification
- Windows support
- Release-asset tarballs (using default branch tarball for now)
