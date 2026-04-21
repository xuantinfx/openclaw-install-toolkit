# env-risk: install.sh on fresh macOS / Linux devices

**Reviewed:** `/Users/mac/Documents/AI project x a Kent/openclaw-toolkit/install.sh` (6 commits ahead of main, zip-delivered).
**Scope:** runtime env gotchas a non-technical one-shot user is likely to hit.

## Summary

| Bucket | Count |
|---|---|
| LIKELY | 4 |
| POSSIBLE | 6 |
| UNLIKELY | 4 |
| Safe / verified | 7 |

---

## LIKELY findings

### L1. `jq` pre-check triggers on every Sonoma and older macOS
**Finding:** `preflight` hard-dies on missing `jq`. `jq` is only shipped as `/usr/bin/jq` from macOS **15.0 Sequoia** onward (Sep 2024). Sonoma (14.x), Ventura, Monterey, Big Sur, Catalina users have **no jq**, and the hint is `brew install jq` — but they may also have no Homebrew (see L2).
**Impact:** The majority of Macs in the wild as of early 2026 still run Sonoma/Ventura. Every such user hits `error: missing required command: jq` as their first experience.
**Mitigation:** Either (a) vendor `jq` into the zip (it's 1.5 MB universal), or (b) replace jq usage with a pure-bash JSON emitter for `backup_and_write_config` (the only heavy jq use — `getMe` parsing is one `grep -o` away), or (c) auto-install jq via a fallback path before dying. At minimum, detect no-brew and escalate the error message.

### L2. Hint `brew install jq` assumes Homebrew exists
**Finding:** On a truly fresh Mac, `/opt/homebrew` doesn't exist. Our hint tells them to `brew install jq`, but `brew` isn't on `$PATH` either — the user sees `zsh: command not found: brew` and stalls.
**Impact:** Compounds L1. A non-technical user cannot recover without hand-holding.
**Mitigation:** Detect absence of `brew` in the jq-missing path and give a complete copy-pasteable remediation (install Homebrew curl one-liner + `brew install jq` + re-run `install.sh`), or bundle jq as per L1.

### L3. `ensure_openclaw_on_path` uses `$SHELL` — wrong source of truth
**Finding:** `case "${SHELL:-}"` picks the rc file from the login shell recorded in `/etc/passwd`. On macOS 10.15+ the login shell is zsh by default, but many users explicitly `chsh -s /bin/bash` or launch `bash` from Terminal.app while `$SHELL=/bin/zsh`. We write to `~/.zshrc`; the user's actual interactive shell (bash) never sources it.
**Impact:** User re-opens Terminal, types `openclaw`, gets "command not found", assumes install failed, even though everything worked.
**Mitigation:** Write to both `~/.zshrc` **and** `~/.bash_profile` / `~/.bashrc` if they exist, or probe parent `ps -p $PPID -o comm=` to detect the actual invoking shell. The "source %s" hint at the end is good but the parent shell from `curl|bash` is unreachable — and the `install.command` path runs in a throwaway Terminal window that exits.

### L4. `install.command` and `install.sh` not dequarantined
**Finding:** Zips downloaded via browser or received over iMessage/AirDrop carry the `com.apple.quarantine` xattr. `install.command` double-click hits the "unidentified developer" Gatekeeper wall. `instruction.txt` § STEP 2 Way B documents the right-click→Open workaround, but if the user picks Way B first and panics, they may abandon. The script never self-dequarantines (it can't — it has to run first to do so).
**Impact:** Well documented, but still a very common first-five-minutes stumble. First impression is "this looks sketchy".
**Mitigation:** Make `install.command` the recommended path in instruction.txt Way A (currently Way A is drag-to-terminal), OR add a README.md note + promote the "right-click Open" dialog to STEP 2 rather than buried under "Way B may need one extra click". Optionally add a tiny `dequarantine.command` shim the user runs first.

---

## POSSIBLE findings

- **P1. `npm prefix -g` is called without `require_cmd npm`.** On a fresh Mac with no Node, `resolve_openclaw_binary` and `run_official_installer` both invoke `npm`. The `|| true` swallows the error, and we fall through to other candidates, so this is currently benign — but if the upstream installer also depends on npm, the user will hit an error deep inside `curl … | bash` with a less helpful message. Worth adding a `require_cmd npm` early if upstream actually needs it.

- **P2. Homebrew path differences (Apple Silicon `/opt/homebrew` vs Intel `/usr/local`) are handled for lookup but not for remediation hints.** The "install with: brew install jq" hint works on both since `brew` self-locates, so this is OK. Noted for completeness.

- **P3. No `LC_ALL=C` guard on `grep -Eq` regex validation.** Under exotic `LC_CTYPE` (e.g. `C.UTF-8` on some Linux distros, `POSIX`), character classes in `[A-Za-z0-9_-]` are safe but edge-case locales could misbehave. Low severity — the Telegram/Anthropic tokens are all ASCII by spec.

- **P4. `~` with non-ASCII characters / spaces in `$HOME`.** Everywhere we pass `$HOME` or `$OPENCLAW_HOME` to `cp -R`, `mkdir -p`, `mv`, `rm -rf` the value is double-quoted and survives spaces/unicode — good. **But** `$OPENCLAW_HOME/bin/openclaw` ends up in the `~/.zshrc` line as a **literal** path when `OPENCLAW_HOME` is overridden (line 623). If the override has a space or unicode, the exported `PATH="/Users/人名/foo bar/bin:$PATH"` in zshrc works, but a user inspecting the file will see it unquoted-looking. Functionally OK; cosmetically scary. Only a concern if someone sets `OPENCLAW_HOME_OVERRIDE` — default path is fine.

- **P5. `openclaw dashboard` trusts upstream to have completed.** `open_dashboard` runs after `start_daemon`, `wait_for_healthz`, and verify steps, so the upstream installer has definitely finished. The `|| :` absorption via `if ! openclaw dashboard` is correct. **But** if a user runs `OPENCLAW_NO_DASHBOARD=1 install.sh` and later tries `openclaw dashboard` manually, the ensure-PATH edit must have taken effect — which requires a new shell window. Worth mentioning in `on_success`.

- **P6. `/dev/tcp` availability on custom bash builds.** Stock Apple `/bin/bash` 3.2.57 has `/dev/tcp` enabled (verified on macOS 15.4). Homebrew bash is also built with `--enable-net-redirections`. MacPorts/Nix/Gentoo users running shebang `/usr/bin/env bash` that resolves to a custom build **could** hit "no such file /dev/tcp/127.0.0.1/N" — `is_port_free` would then incorrectly return "free" (connection attempt fails as error, not refused). A user in that group is technical enough to self-diagnose; still worth a fallback to `lsof` or `nc`.

---

## UNLIKELY findings

- **U1. Corporate proxy vs `--proto '=https' --tlsv1.2 --max-time 30`.** curl honors `HTTP_PROXY` / `HTTPS_PROXY` transparently; these flags don't conflict. Safe.
- **U2. IPv6-only networks.** api.anthropic.com and api.telegram.org have AAAA records; curl handles both stacks. Safe.
- **U3. Clock skew breaking TLS.** Real but rare on modern Macs (NTP runs by default). Error message would say "curl: (60) SSL certificate problem" — terse but at least identifiable.
- **U4. Keychain prompts from `openclaw gateway install`.** Out of scope of this script (upstream behaviour). If upstream ever starts provisioning a login-keychain item, a Touch ID prompt mid-installer would surprise users; flag for upstream team.

---

## Safe / verified

- **V1.** Stock macOS `/bin/bash` 3.2.57 supports `/dev/tcp` (verified on 15.4). `is_port_free` works.
- **V2.** `mktemp -d` and `mktemp -d -t openclaw` both work on stock macOS. Fallback chain is correct.
- **V3.** `date -u +%Y%m%dT%H%M%SZ` output is locale-independent (numeric/ASCII only).
- **V4.** `cp -p` and `cp -R` are BSD-flavoured on mac, GNU on Linux — flags used (`-p`, `-R`) are portable across both.
- **V5.** `find … -type l | wc -l | tr -d ' '` correctly handles the BSD-vs-GNU whitespace-padding-on-wc difference. Good catch by the author.
- **V6.** `launchctl` is present on all macOS versions; `systemd` assumption is delegated to upstream installer (fine).
- **V7.** Double-invocation (double-click install.command twice) is mostly safe: `backup_and_write_config` timestamps backups to the second; `maybe_reset_existing_install` prompts on both; `openclaw gateway install` is documented idempotent. Could race on `.tmp`→`mv` but probability is low (only if two invocations hit `backup_and_write_config` in the exact same second).

---

## Unresolved questions

1. **Fallback for Sonoma-and-older (no bundled jq)?** Vendor jq binary in zip (simplest, +1.5 MB), or swap to pure-bash JSON emitter (YAGNI-friendly, but harder to maintain)?
2. **Do we want to write PATH export to multiple rc files** (`.zshrc` + `.bash_profile` + `.bashrc`) to handle `$SHELL`-vs-actual-interactive-shell mismatch (L3)?
3. **Should the zip ship a `README.command` or promote Way A (drag-to-terminal) as primary** to sidestep Gatekeeper entirely on first contact (L4)?
4. **Is `npm` strictly required by the upstream `install-cli.sh`?** If yes, we should `require_cmd npm` in preflight with a node.js install hint (P1).
5. **No Linux testing evidence in this repo** — is Linux actually a supported target, or is `detect_os`'s Linux branch aspirational? If aspirational, tighten `detect_os` to Darwin-only.

---

**Status:** DONE
**Summary:** Reviewed `install.sh` (732 LOC) for fresh-device install risks. Four LIKELY findings dominate — the top two are jq availability on pre-Sequoia macOS and the Homebrew-missing cascade; the other two are `$SHELL` vs actual-shell rc-file mismatch and quarantine xattr on install.command. Six possibles and four unlikelys catalogued; seven items verified safe on macOS 15.4 stock bash 3.2.
**Concerns/Blockers:** None — review task complete. Unresolved questions listed above need user decisions before any remediation implementation.
