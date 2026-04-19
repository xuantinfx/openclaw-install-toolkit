---
phase: 02
status: done
priority: medium
effort: S
---

# Phase 02 — Create install.command wrapper

## Overview
Ship a double-click-friendly `.command` file that opens Terminal and runs `install.sh` from the zip folder. Secondary entry point (primary remains drag-to-Terminal).

## Files
- Create: `/Users/mac/Documents/AI project x a Kent/openclaw-toolkit/install.command`

## Requirements
- Must resolve its own directory — `cd "$(dirname "$0")"` (macOS `.command` files run with arbitrary CWD, typically `$HOME`).
- Must invoke `bash install.sh` (not `./install.sh`) to sidestep exec-bit loss from unzip tools.
- Terminal window stays open on failure so user can read the error (add `read -p "Press Enter to close..."` after the script call).
- No extra logic — all install work belongs in `install.sh`.
- File must have exec bit (`chmod +x install.command`) committed to repo so zip build preserves it.

## Implementation Steps

### 1. Create file
```bash
#!/usr/bin/env bash
# openclaw installer — double-click wrapper. Real work lives in install.sh.
cd "$(dirname "$0")" || exit 1
bash install.sh
status=$?
printf '\n'
read -r -p "Press Enter to close this window..."
exit "$status"
```

### 2. Set exec bit
```bash
chmod +x install.command
```

### 3. Verify git stores exec bit
After commit: `git ls-tree HEAD install.command` should show `100755`, not `100644`.

## Todo List
- [ ] Write `install.command` with shebang + cd + bash install.sh + read pause
- [ ] `chmod +x install.command`
- [ ] Stage and confirm git mode is 100755
- [ ] `bash -n install.command` syntax check

## Success Criteria
- Double-click `install.command` from Finder on macOS → Terminal opens, install runs, window stays open at the end regardless of success/failure.
- `git ls-tree HEAD install.command` shows `100755` mode.
- Works identically when run from an unzipped folder with spaces in path (e.g., `~/Downloads/my folder/openclaw-toolkit/`).

## Risks
- Gatekeeper quarantine on first double-click — not fixable in script; documented in phase-03 (instruction.txt). Users right-click → Open once.
- Some zip utilities strip exec bit even from zips built with `zip -X`. Fallback: instruction.txt directs users to drag-to-Terminal with `bash ` prefix (no exec bit needed).
