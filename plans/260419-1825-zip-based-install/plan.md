---
status: code-complete (live E2E deferred)
created: 2026-04-19
scope: zip-based-install-flow
brainstorm: ../reports/brainstorm-260419-1825-zip-based-install.md
validation: ../reports/validation-260419-zip-based-install.md
blockedBy: []
blocks: []
---

# Zip-based Install Flow — Implementation Plan

Replace curl-based install (2 hits to `github.com/xuantinfx`) with a single per-user zip delivered by message. Ships `install.sh` + `install.command` + local `skills/`. Only runtime network calls hit `openclaw.ai` installer + Telegram/Anthropic verify endpoints.

## Context Links
- Brainstorm report: `../reports/brainstorm-260419-1825-zip-based-install.md`
- Superseded plans (completed): `../20260412-openclaw-installer/`, `../20260412-1520-skills-subtree-and-installer/`
- Files in play: `install.sh`, `install-skill.sh` (delete), `instruction.txt`, `README.md`, new `install.command`

## Key Locked Decisions
- Merge `install-skill.sh` into `install.sh` (single entry point).
- Keep `curl openclaw.ai/install-cli.sh | bash` — only allowed external call.
- Still prompt for Telegram token + Anthropic key (no baked secrets).
- Primary UX: drag `install.sh` to Terminal with `bash ` prefix (exec-bit-independent).
- Secondary UX: double-click `install.command` (needs exec bit; Gatekeeper right-click → Open on first run).
- Bash 3.2 compat, preserve 0600 config perms + git-worktree refusal.
- Out of scope: `scripts/build-zip.sh` (separate task).

## Phases
| # | Name | File | Status |
|---|---|---|---|
| 01 | Edit install.sh — merge skills logic | `phase-01-edit-install-sh.md` | done |
| 02 | Create install.command wrapper | `phase-02-create-install-command.md` | done |
| 03 | Rewrite instruction.txt | `phase-03-rewrite-instruction.md` | done |
| 04 | Cleanup — delete install-skill.sh, update README, retune CI | `phase-04-cleanup.md` | done |
| 05 | Manual validation | `phase-05-validation.md` | automated PASS; live E2E deferred |

## Dependencies
- Phase 01 → 02 (command wrapper just invokes install.sh, but no hard dep).
- Phase 03 requires 01+02 done (docs describe real scripts).
- Phase 04 requires 01 done (install-skill.sh merged before deletion).
- Phase 05 requires all prior phases.

## Success Criteria
- Fresh macOS: unzip → drag `install.sh` to Terminal → bot replies to "hi" within 2 min.
- Packet capture shows zero requests to `github.com/xuantinfx/*` during install.
- `~/.openclaw/skills/content-monitor/SKILL.md` present post-install.
- Re-run install on same machine → config backup created, no errors.

## Risk Summary
- Gatekeeper quarantine on `.command` → documented in instruction.txt.
- Exec bit loss on unzip → primary drag-to-Terminal path unaffected; fallback documented.
- Missing `./skills/` in zip → `install_local_skills()` fails loudly.

## Accepted Risks (owner approved 2026-04-19)
- **Tampered zip → RCE on user machine.** OpenClaw gateway executes scripts inside installed skills (`~/.openclaw/skills/<x>/scripts/*`). A messaging-channel MITM or a compromised build host can swap zip contents → arbitrary code runs on the user's Mac after install. Owner decision: skip cryptographic verification (no SHA256 prompt, no MANIFEST, no signing) because: (a) user count is small + delivery channels are trusted, (b) UX friction of pasting a hash outweighs the marginal security gain for this threat model, (c) same trust assumption already applies to the openclaw.ai installer curl'd at step 4.
- **Mitigation boundaries:** if user count grows, delivery channel changes, or build host moves off a trusted machine → revisit. Re-add `--verify-hash`/`MANIFEST.sha256` flow (ck:predict review 2026-04-19-2050 has the design sketch).

## Predict-review outcomes (ck:predict 2026-04-19-2050)
- Verdict: CAUTION → GO once accepted-risks documented (done above).
- Non-STOP recommendations still open for owner to decide later:
  - Demote `install.command` in `instruction.txt` STEP 2 happy-path (keep as troubleshooting fallback) — reduces Gatekeeper-bypass training, simpler for non-technical readers.
  - Capture WHY "no GitHub hits" requirement exists (rate limits / privacy / branding?) — one sentence so future maintainers can validate alternatives.
  - Phase-05 negative case: manually corrupt one file inside staged zip, confirm `install_local_skills()` still installs it (current design only rejects missing SKILL.md + symlinks — no content verification, consistent with accepted-risks above).

## Open Questions
- Zip top-level folder name + `README.txt` inclusion — defer to build-zip task.
