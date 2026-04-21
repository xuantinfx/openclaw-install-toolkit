#!/usr/bin/env bash
# OpenClaw installer — thin wrapper around the official install-cli.sh.
# Collects Telegram + Anthropic credentials, writes ~/.openclaw/openclaw.json,
# starts the daemon, and verifies end-to-end connectivity.
#
# Bash 3.2 compatible (stock macOS). Requires: curl, jq.
# Secrets are inlined in openclaw.json (mode 0600). Do not commit the config.

set -euo pipefail
IFS=$'\n\t'

OPENCLAW_HOME="${OPENCLAW_HOME_OVERRIDE:-${OPENCLAW_HOME:-$HOME/.openclaw}}"
DEFAULT_PORT=18789
DEFAULT_INSTALL_URL="https://openclaw.ai/install-cli.sh"
MODEL="anthropic/claude-sonnet-4-6"

# Resolve the directory this script lives in so we can find the bundled
# ./skills/ folder regardless of CWD. Only treat BASH_SOURCE[0] as valid
# when it points at a real file — under `curl|bash`, BASH_SOURCE is unset
# and $0 is "bash", so without this check dirname would fall through to
# CWD and install whatever hostile ./skills/ happens to be there.
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

PORT="$DEFAULT_PORT"
# 1 when the user passed --port explicitly. Gates reinstall-stability
# (reusing a port from an existing openclaw.json) so an explicit override
# always wins over a stored value, even if the override equals DEFAULT_PORT.
EXPLICIT_PORT=0
DRY_RUN=0
BOT_USERNAME=""
RESET=0
KEEP_DATA=0
# Holds OPENCLAW_HOME as the user supplied it, before the dry-run remap below
# replaces it with a tmpdir. Detection + recovery snapshot must use the real
# path, otherwise --dry-run --reset previews "no config found" on every box.
ORIGINAL_OPENCLAW_HOME=""

# Coerce truthy spellings to 1; everything else (including unset) stays 0.
# Without this, OPENCLAW_RESET=true triggers `[: integer expression expected`
# under set -e on the arithmetic checks below.
case "${OPENCLAW_RESET:-}" in
  1|true|TRUE|True|yes|YES|Yes|on|ON|On) RESET=1 ;;
esac
case "${OPENCLAW_KEEP_DATA:-}" in
  1|true|TRUE|True|yes|YES|Yes|on|ON|On) KEEP_DATA=1 ;;
esac

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: install.sh [--port N] [--dry-run] [--reset|--keep-data] [--help]

Options:
  --port N       Preferred gateway port (default 18789). If busy, the
                 installer probes N..N+9 and picks the first free one.
  --dry-run      Collect inputs and show generated config; skip installer + daemon
  --reset        Wipe existing install (openclaw reset --scope full) without prompting
  --keep-data    Keep existing install data without prompting (default under no-TTY)
  --help, -h     Show this message

Environment:
  TELEGRAM_BOT_TOKEN     If set, skip interactive prompt
  ANTHROPIC_API_KEY      If set, skip interactive prompt
  OPENCLAW_INSTALL_URL   Override official installer URL
  OPENCLAW_HOME          Override install dir (default: $HOME/.openclaw)
  OPENCLAW_RESET=1       Same as --reset
  OPENCLAW_KEEP_DATA=1   Same as --keep-data
  OPENCLAW_NO_DASHBOARD=1  Skip auto-opening the Control UI after install

When an existing install is detected ($OPENCLAW_HOME/openclaw.json), the
installer prompts y/N to wipe before reinstalling. Default = N (keep data).
Without a TTY (e.g. curl|bash), the wipe is auto-skipped — pass --reset to force.

Multi-user Macs: each macOS account gets its own gateway port automatically.
See instruction-multi-user.txt for the full walk-through.
EOF
}

cleanup() {
  unset TELEGRAM_BOT_TOKEN ANTHROPIC_API_KEY 2>/dev/null || true
}
trap cleanup EXIT

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --port)
        [ $# -ge 2 ] || die "--port requires a value"
        PORT="$2"
        EXPLICIT_PORT=1
        shift 2
        ;;
      --port=*)
        PORT="${1#--port=}"
        EXPLICIT_PORT=1
        shift
        ;;
      --dry-run)
        DRY_RUN=1
        shift
        ;;
      --reset)
        RESET=1
        shift
        ;;
      --keep-data)
        KEEP_DATA=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        usage >&2
        die "unknown argument: $1"
        ;;
    esac
  done

  case "$PORT" in
    ''|*[!0-9]*) die "invalid port: $PORT (must be integer)" ;;
  esac
  if [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    die "invalid port: $PORT (must be 1-65535)"
  fi

  if [ "$RESET" -eq 1 ] && [ "$KEEP_DATA" -eq 1 ]; then
    die "--reset and --keep-data are mutually exclusive"
  fi
}

detect_os() {
  local os
  os="$(uname -s)"
  case "$os" in
    Darwin|Linux) printf '%s\n' "$os" ;;
    *) die "unsupported OS: $os (only macOS and Linux are supported)" ;;
  esac
}

require_cmd() {
  local cmd="$1"
  local hint="$2"
  command -v "$cmd" >/dev/null 2>&1 || die "missing required command: $cmd — $hint"
}

# Download a known-good jq into $OPENCLAW_HOME/bin and amend PATH if the
# system has no usable jq. Pre-Sequoia macOS (Sonoma, Ventura, older) and
# bare Linux boxes routinely ship without jq; asking a non-technical user
# to "brew install jq" when they also have no Homebrew is a dead end.
# Best-effort: we fall through to the caller's require_cmd (with its
# improved hint) if the download fails for any reason.
JQ_VERSION="jq-1.7.1"
bootstrap_jq_if_missing() {
  # Valid jq already on PATH — nothing to do.
  if command -v jq >/dev/null 2>&1 && jq --version >/dev/null 2>&1; then
    return 0
  fi

  local asset_name url
  case "$(uname -sm 2>/dev/null)" in
    "Darwin arm64")   asset_name="jq-macos-arm64" ;;
    "Darwin x86_64")  asset_name="jq-macos-amd64" ;;
    "Linux x86_64")   asset_name="jq-linux-amd64" ;;
    "Linux aarch64")  asset_name="jq-linux-arm64" ;;
    *) return 1 ;;
  esac
  url="https://github.com/jqlang/jq/releases/download/${JQ_VERSION}/${asset_name}"

  local dest_dir="$OPENCLAW_HOME/bin"
  if ! mkdir -p "$dest_dir" 2>/dev/null; then
    printf '[bootstrap] cannot create %s — skipping jq auto-install\n' "$dest_dir" >&2
    return 1
  fi
  local dest="$dest_dir/jq"

  printf '[bootstrap] jq not found; downloading %s (%s) to %s...\n' "$JQ_VERSION" "$asset_name" "$dest" >&2
  if ! curl -fsSL --proto '=https' --tlsv1.2 --max-time 60 "$url" -o "$dest.tmp"; then
    rm -f "$dest.tmp" 2>/dev/null
    printf '[bootstrap] download failed (url: %s)\n' "$url" >&2
    return 1
  fi
  chmod +x "$dest.tmp" 2>/dev/null || { rm -f "$dest.tmp"; return 1; }
  mv "$dest.tmp" "$dest" 2>/dev/null || { rm -f "$dest.tmp"; return 1; }

  # Prepend bin dir to PATH for this script run. Persistent PATH happens
  # later in ensure_openclaw_on_path (same dir), so future terminals
  # inherit jq alongside openclaw.
  PATH="$dest_dir:$PATH"
  export PATH
  hash -r 2>/dev/null || true

  if ! jq --version >/dev/null 2>&1; then
    printf '[bootstrap] downloaded jq binary at %s is not executable on this machine\n' "$dest" >&2
    return 1
  fi
  printf '[bootstrap] jq ready at %s\n' "$dest" >&2
  return 0
}

preflight() {
  local os
  os="$(detect_os)"

  local jq_hint curl_hint
  if [ "$os" = "Darwin" ]; then
    # Pre-Sequoia (< 15) Macs ship without jq. The hint doubles as
    # "install Homebrew first" guidance since many fresh Macs also lack
    # brew. Shown only if bootstrap_jq_if_missing also failed.
    jq_hint="auto-download failed. Install manually: install Homebrew (https://brew.sh) then run 'brew install jq', or grab a binary from https://jqlang.org/download and re-run install.sh"
    curl_hint="install with: brew install curl (or Homebrew itself from https://brew.sh)"
  else
    jq_hint="auto-download failed. Install manually: 'sudo apt install jq' (Debian/Ubuntu), 'sudo dnf install jq' (Fedora), or see https://jqlang.org/download"
    curl_hint="install with: sudo apt install curl (or your distro equivalent)"
  fi

  require_cmd curl "$curl_hint"
  bootstrap_jq_if_missing || true
  # Verify jq is functional (not merely present). A fake/broken jq on PATH
  # otherwise satisfies require_cmd but fails later inside backup_and_write_config
  # with a confusing error. Running `jq --version` reliably detects both
  # "absent" and "broken" cases.
  if ! jq --version >/dev/null 2>&1; then
    die "missing required command: jq — $jq_hint"
  fi

  # Walk up to the nearest existing ancestor so we catch cases where
  # $OPENCLAW_HOME doesn't exist yet but its parent is inside a git repo.
  local probe="$OPENCLAW_HOME"
  while [ -n "$probe" ] && [ "$probe" != "/" ] && [ ! -d "$probe" ]; do
    probe="$(dirname "$probe")"
  done
  if [ -d "$probe" ]; then
    if (cd "$probe" && git rev-parse --is-inside-work-tree >/dev/null 2>&1); then
      die "$OPENCLAW_HOME is inside a git worktree; refusing to write plaintext secrets there"
    fi
  fi
}

# Probe a TCP port on loopback via the bash /dev/tcp builtin. Success
# opening the socket means a listener answered => port is busy. Connection
# refused => port is free. Keeps us dependency-free (no lsof/nc required).
is_port_free() {
  local port="$1"
  if (exec 3<>/dev/tcp/127.0.0.1/"$port") 2>/dev/null; then
    exec 3<&- 2>/dev/null    # close probe fd
    return 1                 # busy
  fi
  return 0                   # free
}

# Scan `tries` ports starting at `start`; print the first free one.
# Returns non-zero if none are free in range (caller decides how to die).
find_free_port() {
  local start="$1" tries="${2:-10}" i=0 p
  while [ "$i" -lt "$tries" ]; do
    p=$((start + i))
    [ "$p" -gt 65535 ] && break
    if is_port_free "$p"; then
      printf '%s\n' "$p"
      return 0
    fi
    i=$((i + 1))
  done
  return 1
}

# Resolve the final gateway port before config write / daemon start.
# Order of preference: (1) still-free port from existing openclaw.json when
# --port wasn't overridden (reinstall stability), (2) scan-and-bump from
# the requested port. Applies to both default and explicit --port per the
# design brief — always probe, warn+bump if busy.
resolve_port() {
  local requested="$PORT"
  local home="${ORIGINAL_OPENCLAW_HOME:-$OPENCLAW_HOME}"
  local cfg="$home/openclaw.json"
  local existing=""

  if [ "$EXPLICIT_PORT" -eq 0 ] && [ -f "$cfg" ]; then
    existing="$(jq -r '.gateway.port // empty' "$cfg" 2>/dev/null || true)"
    # Drop anything that isn't a plain positive integer in the valid TCP
    # range. A tampered / hand-edited config with "port": 0, "port": 70000,
    # or "port": "\"; rm -rf /\"" must not flow into is_port_free / PORT.
    case "$existing" in
      ''|*[!0-9]*) existing="" ;;
    esac
    if [ -n "$existing" ] && { [ "$existing" -lt 1 ] || [ "$existing" -gt 65535 ]; }; then
      existing=""
    fi
    if [ -n "$existing" ] && is_port_free "$existing"; then
      if [ "$existing" != "$requested" ]; then
        printf '[port] reusing previously-assigned port %s (from %s)\n' "$existing" "$cfg" >&2
      fi
      PORT="$existing"
      return 0
    fi
  fi

  local chosen
  if chosen="$(find_free_port "$requested" 10)"; then
    if [ "$chosen" != "$requested" ]; then
      printf '[port] %s is busy; using %s instead\n' "$requested" "$chosen" >&2
    fi
    PORT="$chosen"
  else
    # Clamp at 65535 so the message reflects what was actually probed —
    # find_free_port breaks early when the candidate would overflow.
    local end=$((requested + 9))
    [ "$end" -gt 65535 ] && end=65535
    die "no free port in $requested-$end. Check 'lsof -iTCP:$requested-$end -sTCP:LISTEN' and free one up."
  fi
}

prompt_secret() {
  local var_name="$1"
  local label="$2"
  local current
  eval "current=\${${var_name}:-}"
  if [ -n "$current" ]; then
    return 0
  fi
  # Read from /dev/tty so the prompt works under `curl ... | bash`
  # (where stdin is the download pipe, not the keyboard).
  if [ ! -r /dev/tty ] || [ ! -w /dev/tty ]; then
    die "$label is required but no TTY is attached. Set $var_name=... as an env var instead."
  fi
  printf '%s: ' "$label" >/dev/tty
  local value
  # shellcheck disable=SC2162
  IFS= read -r value </dev/tty
  printf '\n' >/dev/tty
  [ -n "$value" ] || die "$label cannot be empty"
  eval "$var_name=\$value"
}

collect_secrets() {
  prompt_secret TELEGRAM_BOT_TOKEN "Telegram bot token"
  prompt_secret ANTHROPIC_API_KEY "Anthropic API key"
}

validate_secrets() {
  printf '%s' "$TELEGRAM_BOT_TOKEN" | grep -Eq '^[0-9]{5,}:[A-Za-z0-9_-]{30,}$' \
    || die "invalid Telegram bot token format (expected <digits>:<token>)"

  case "$ANTHROPIC_API_KEY" in
    sk-ant-*)
      if [ ${#ANTHROPIC_API_KEY} -lt 20 ]; then
        die "Anthropic API key too short"
      fi
      ;;
    *) die "invalid Anthropic API key format (expected prefix: sk-ant-)" ;;
  esac
}

resolve_openclaw_binary() {
  # Returns 0 if the openclaw binary is callable (possibly after PATH amendment),
  # 1 otherwise. Mirrors the search in run_official_installer so a prior install
  # under the upstream's self-contained prefix is still findable here.
  command -v openclaw >/dev/null 2>&1 && return 0
  local prefix cand
  prefix="$(npm prefix -g 2>/dev/null || true)"
  for cand in \
    "$OPENCLAW_HOME/bin" \
    "${prefix:+$prefix/bin}" \
    "$HOME/.npm-global/bin" \
    "$HOME/.local/bin" \
    "/opt/homebrew/bin" \
    "/usr/local/bin"; do
    if [ -n "$cand" ] && [ -x "$cand/openclaw" ]; then
      PATH="$cand:$PATH"
      export PATH
      hash -r 2>/dev/null || true
      return 0
    fi
  done
  return 1
}

maybe_reset_existing_install() {
  # Probe the user's real install dir, not the dry-run mktemp remap.
  # ORIGINAL_OPENCLAW_HOME is captured in main() before the remap fires.
  local home="${ORIGINAL_OPENCLAW_HOME:-$OPENCLAW_HOME}"
  local cfg="$home/openclaw.json"
  # No prior config => nothing to wipe. Probe the file (not the dir) because
  # the upstream installer sometimes leaves an empty bin/ behind on a fresh box.
  [ -f "$cfg" ] || return 0

  local decision=""
  [ "$RESET" -eq 1 ] && decision="reset"
  [ "$KEEP_DATA" -eq 1 ] && decision="skip"
  [ -z "$decision" ] && decision="ask"

  if [ "$decision" = "ask" ]; then
    # `[ -r /dev/tty ]` is unreliable on macOS — the device node always exists
    # and is access(2)-readable, but open(2) fails with ENXIO when the process
    # has no controlling terminal (CI, nohup, harness shells). Probe by
    # actually opening it.
    if : </dev/tty >/dev/tty 2>/dev/null; then
      printf '[warn] existing OpenClaw install detected at %s\n' "$home" >/dev/tty
      printf '[warn] wipe config, skills, credentials, sessions before reinstalling? [y/N]: ' >/dev/tty
      local ans=""
      # shellcheck disable=SC2162
      IFS= read -r ans </dev/tty || ans=""
      printf '\n' >/dev/tty
      case "$ans" in
        y|Y|yes|YES) decision="reset" ;;
        # Default N is load-bearing: silently wiping a user's data on every
        # rerun would be a footgun. Don't flip without a release-note plan.
        *)           decision="skip"  ;;
      esac
      # Mirror to stderr so audit logs (CI, tee'd installs) preserve choice.
      printf '[reset] user choice: %s\n' "$decision" >&2
    else
      printf '[info] existing install detected at %s — skipping wipe (no TTY). Pass --reset to force.\n' "$home" >&2
      decision="skip"
    fi
  fi

  if [ "$decision" = "skip" ]; then
    printf '[info] keeping existing data at %s\n' "$home" >&2
    return 0
  fi

  # decision=reset
  if ! resolve_openclaw_binary; then
    if [ "$RESET" -eq 1 ]; then
      die "cannot reset: openclaw binary not found (config at $cfg is orphaned). Manual cleanup: rm -rf $home, then re-run install.sh"
    fi
    printf '[warn] config at %s but no openclaw binary on PATH — skipping reset\n' "$cfg" >&2
    return 0
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] would snapshot %s and run: openclaw reset --scope full --yes --non-interactive\n' "$cfg" >&2
    return 0
  fi

  # Snapshot config before destructive call so the user has a recovery hint
  # if the upstream installer fails after wipe (token, skills, credentials
  # are still lost — but the json blueprint that built them survives).
  local ts snap
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  snap="$cfg.pre-reset.bak.$ts"
  if cp -p "$cfg" "$snap" 2>/dev/null; then
    printf '[reset] config snapshot saved to %s\n' "$snap" >&2
  else
    snap=""
    printf '[warn] could not snapshot %s before reset (continuing anyway)\n' "$cfg" >&2
  fi

  printf '[reset] running openclaw reset --scope full --yes --non-interactive\n' >&2
  if ! openclaw reset --scope full --yes --non-interactive; then
    if [ -n "$snap" ]; then
      die "openclaw reset failed. Pre-reset config snapshot: $snap. Manual cleanup: openclaw uninstall --all --yes --non-interactive && rm -rf $home, then re-run install.sh"
    fi
    die "openclaw reset failed. Manual cleanup: openclaw uninstall --all --yes --non-interactive && rm -rf $home, then re-run install.sh"
  fi
  printf '[reset] done\n' >&2
}

run_official_installer() {
  local url="${OPENCLAW_INSTALL_URL:-$DEFAULT_INSTALL_URL}"
  printf '[install] fetching %s\n' "$url" >&2
  # pipefail ensures a curl failure propagates even through the pipe to bash.
  curl -fsSL --proto '=https' --tlsv1.2 --max-time 30 "$url" | bash \
    || die "official installer failed (url: $url)"

  # Upstream writes a wrapper to $OPENCLAW_HOME/bin/openclaw (~/.openclaw/bin
  # by default) — a self-contained prefix that isn't on PATH by default.
  # Other setups (nvm, npm-global, Homebrew) put it under npm's global prefix.
  # Check these before the fatal PATH gate.
  local prefix=""
  local found=""
  if ! command -v openclaw >/dev/null 2>&1; then
    prefix="$(npm prefix -g 2>/dev/null || true)"
    local cand
    for cand in \
      "$OPENCLAW_HOME/bin" \
      "${prefix:+$prefix/bin}" \
      "$HOME/.npm-global/bin" \
      "$HOME/.local/bin" \
      "/opt/homebrew/bin" \
      "/usr/local/bin"; do
      if [ -n "$cand" ] && [ -x "$cand/openclaw" ]; then
        PATH="$cand:$PATH"
        found="$cand/openclaw"
        break
      fi
    done
    export PATH
    hash -r 2>/dev/null || true
  fi

  if ! command -v openclaw >/dev/null 2>&1; then
    printf '[install] openclaw binary not found after install.\n' >&2
    printf '[install] checked these locations:\n' >&2
    printf '[install]   %s/bin  (OPENCLAW_HOME)\n' "$OPENCLAW_HOME" >&2
    printf '[install]   npm prefix -g -> %s\n' "${prefix:-<npm not found>}" >&2
    printf '[install]   %s/.npm-global/bin\n' "$HOME" >&2
    printf '[install]   %s/.local/bin\n' "$HOME" >&2
    printf '[install]   /opt/homebrew/bin  /usr/local/bin\n' >&2
    printf '[install] hint: upstream installs a wrapper at %s/bin/openclaw\n' "$OPENCLAW_HOME" >&2
    printf '[install]       — make sure that directory exists and is executable.\n' >&2
    printf '[install] open a new Terminal window and re-run, or add the missing\n' >&2
    printf '[install] directory to PATH in ~/.zshrc.\n' >&2
    die "openclaw not on PATH after install"
  fi
  [ -n "$found" ] && printf '[install] found openclaw at %s\n' "$found" >&2
  openclaw --version >/dev/null 2>&1 \
    || die "openclaw --version failed after install"
}

backup_and_write_config() {
  mkdir -p "$OPENCLAW_HOME" || die "cannot create $OPENCLAW_HOME"

  local cfg="$OPENCLAW_HOME/openclaw.json"
  if [ -f "$cfg" ]; then
    local ts backup
    ts="$(date -u +%Y%m%dT%H%M%SZ)"
    backup="$cfg.bak.$ts"
    mv "$cfg" "$backup" || die "failed to back up existing config to $backup"
    printf '[config] existing config backed up to %s\n' "$backup" >&2
  fi

  local tmp="$cfg.tmp"
  jq -n \
    --argjson port "$PORT" \
    --arg model "$MODEL" \
    --arg botToken "$TELEGRAM_BOT_TOKEN" \
    --arg anthropicKey "$ANTHROPIC_API_KEY" \
    '{
      gateway:  { port: $port, bind: "loopback", mode: "local" },
      agents:   {
        defaults: { model: { primary: $model } },
        list: [ { id: "main", tools: { profile: "full" } } ]
      },
      channels: { telegram: { enabled: true, botToken: $botToken } },
      env:      { ANTHROPIC_API_KEY: $anthropicKey }
    }' > "$tmp" || { rm -f "$tmp"; die "failed to build openclaw.json"; }

  mv "$tmp" "$cfg" || { rm -f "$tmp"; die "failed to move config into place"; }
  chmod 0600 "$cfg" || die "failed to chmod 0600 $cfg"
  printf '[config] wrote %s (mode 0600)\n' "$cfg" >&2
}

start_daemon() {
  printf '[daemon] installing + starting openclaw gateway...\n' >&2
  # `install` registers the launchd/systemd unit, expands missing config
  # fields (e.g. auth.token), and starts the service. Idempotent on re-run.
  openclaw gateway install >/dev/null 2>&1 \
    || die "openclaw gateway install failed — run 'openclaw gateway install' manually to see details"
}

wait_for_healthz() {
  local url="http://127.0.0.1:$PORT/healthz"
  local i
  printf '[verify] waiting for gateway at %s ' "$url" >&2
  for i in $(seq 1 30); do
    if curl -fsS "$url" -o /dev/null 2>/dev/null; then
      printf '\n[verify] gateway healthy (took %ss)\n' "$i" >&2
      return 0
    fi
    printf '.' >&2
    sleep 1
  done
  printf '\n' >&2
  die "gateway did not become healthy within 30s on port $PORT — try 'openclaw gateway status' or check 'lsof -i :$PORT' for a port conflict"
}

verify_telegram() {
  local resp ok
  resp="$(curl -fsS --max-time 10 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" 2>/dev/null)" \
    || die "Telegram getMe request failed — check network or token"
  ok="$(printf '%s' "$resp" | jq -r '.ok // false')"
  if [ "$ok" != "true" ]; then
    die "Telegram getMe returned ok=false — token invalid or bot disabled?"
  fi
  BOT_USERNAME="$(printf '%s' "$resp" | jq -r '.result.username // empty')"
  [ -n "$BOT_USERNAME" ] || die "Telegram getMe succeeded but returned no username"
}

verify_anthropic() {
  local status
  status="$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H 'anthropic-version: 2023-06-01' \
    'https://api.anthropic.com/v1/models' 2>/dev/null)" \
    || die "Anthropic /v1/models request failed — check network"
  if [ "$status" != "200" ]; then
    die "Anthropic /v1/models returned HTTP $status — key invalid or expired?"
  fi
}

validate_skill_name() {
  local name="$1"
  case "$name" in
    ''|.|..|*/*|*\\*|.*) die "invalid skill name: '$name'" ;;
  esac
  printf '%s' "$name" | grep -Eq '^[a-z0-9][a-z0-9_-]{0,63}$' \
    || die "invalid skill name: '$name' (must match [a-z0-9][a-z0-9_-]{0,63})"
}

install_local_skills() {
  # SCRIPT_DIR is empty when the script is piped via stdin (curl|bash). That
  # flow cannot ship a ./skills/ folder — direct the user to the zip path.
  if [ -z "$SCRIPT_DIR" ]; then
    die "cannot locate script directory — run install.sh from the unzipped folder, not via pipe"
  fi

  local skills_root="$SCRIPT_DIR/skills"
  [ -d "$skills_root" ] \
    || die "skills/ not found next to install.sh (looked in $skills_root) — zip may be corrupt or incomplete"

  # Reject symlinks anywhere in the tree. A compromised/tampered zip could
  # smuggle one pointing at /etc/* and cp -R would dereference it.
  # Use `wc -l` (reads stdin to EOF) instead of `| read -r` — the latter
  # closes the pipe early, giving find SIGPIPE, which under `set -o pipefail`
  # flips the `if` to the nonzero branch and silently bypasses the check.
  local symlink_count
  symlink_count="$(find "$skills_root" -type l 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${symlink_count:-0}" -gt 0 ]; then
    die "skills/ contains symlinks; refusing to install (possible tampering)"
  fi

  local count=0
  local entry name src dst
  for entry in "$skills_root"/*/; do
    [ -d "$entry" ] || continue
    name="$(basename "$entry")"
    validate_skill_name "$name"

    src="$skills_root/$name"
    dst="$OPENCLAW_HOME/skills/$name"

    [ -f "$src/SKILL.md" ] \
      || die "skill '$name' is missing SKILL.md at its root — corrupt zip?"

    if [ "$DRY_RUN" -eq 1 ]; then
      printf '[dry-run] would install skill %s -> %s\n' "$name" "$dst" >&2
    else
      mkdir -p "$OPENCLAW_HOME/skills" || die "cannot create $OPENCLAW_HOME/skills"
      rm -rf "$dst"
      cp -R "$src" "$dst" || die "failed to copy skill $name into place"
      printf '[skills] installed %s -> %s\n' "$name" "$dst" >&2
    fi
    count=$((count + 1))
  done

  [ "$count" -gt 0 ] || die "no skills found under $skills_root — zip may be incomplete"

  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] would install %d skill(s) from %s\n' "$count" "$skills_root" >&2
  else
    printf '[skills] installed %d skill(s) into %s/skills/\n' "$count" "$OPENCLAW_HOME" >&2
  fi
}

ensure_openclaw_on_path() {
  local bin_dir="$OPENCLAW_HOME/bin"
  [ -x "$bin_dir/openclaw" ] || return 0

  # Opt-out for users managing dotfiles themselves (chezmoi, stow, nix, etc.)
  if [ "${OPENCLAW_NO_RC_EDIT:-0}" = "1" ]; then
    printf '[install] OPENCLAW_NO_RC_EDIT=1 — skipping shell rc edit.\n' >&2
    # shellcheck disable=SC2016
    printf '[install] add manually: export PATH="%s:$PATH"\n' "$bin_dir" >&2
    return 0
  fi

  # The line we append. When OPENCLAW_HOME is the default, use literal $HOME
  # so the rc file stays portable across home-directory renames. The single
  # quotes are intentional — $HOME and $PATH must be written literally so
  # they expand at rc-read time, not now.
  local line
  if [ "$OPENCLAW_HOME" = "$HOME/.openclaw" ]; then
    # shellcheck disable=SC2016
    line='export PATH="$HOME/.openclaw/bin:$PATH"'
  else
    line="export PATH=\"$bin_dir:\$PATH\""
  fi

  # Write to every Bourne-family rc the user might actually source, not just
  # the one implied by $SHELL. Rationale: many macOS users have $SHELL=/bin/zsh
  # (login shell) yet launch bash from Terminal.app, or vice versa. Writing
  # to a single file based on $SHELL leaves them with "command not found" on
  # the other shell. Rules:
  #   • Always ensure ~/.zshrc has the line (zsh is macOS default since 10.15,
  #     create if missing — most Macs have one or will expect one).
  #   • ALSO write to ~/.bash_profile and ~/.bashrc if they already exist
  #     (don't create empty files just for an export a non-bash user won't
  #     source; this respects users who intentionally deleted bashrc).
  # Each write is idempotent (grep-skip if line present) and best-effort.
  # Positional iteration over the candidate set — works identically in
  # bash 3.2+ and zsh (avoids zsh's non-POSIX word-splitting default).
  local rc updated_any=0
  for rc in "$HOME/.zshrc" "$HOME/.bash_profile" "$HOME/.bashrc"; do
    # Gate bash files to "only process if pre-existing" so we don't
    # create empty bashrc/bash_profile for users who deliberately don't
    # use bash. .zshrc is always processed — create if missing.
    case "$rc" in
      *.zshrc) ;;
      *) [ -f "$rc" ] || continue ;;
    esac
    if [ ! -e "$rc" ]; then
      : > "$rc" 2>/dev/null || { printf '[install] could not create %s — skipping\n' "$rc" >&2; continue; }
    fi
    if grep -qxF "$line" "$rc" 2>/dev/null; then
      continue   # already present, leave alone
    fi
    if printf '\n# Added by openclaw-install-toolkit\n%s\n' "$line" >> "$rc" 2>/dev/null; then
      printf '[install] appended PATH export to %s\n' "$rc" >&2
      updated_any=1
    else
      printf '[install] could not write to %s — skipping\n' "$rc" >&2
    fi
  done

  # Fish / nushell / ksh users: syntax differs. Print a manual hint rather
  # than leave them confused when their shell can't source our .zshrc line.
  case "${SHELL:-}" in
    */fish|fish)
      printf '[install] fish detected — add to ~/.config/fish/config.fish manually:\n' >&2
      # shellcheck disable=SC2016
      printf '[install]     set -gx PATH "%s" $PATH\n' "$bin_dir" >&2
      ;;
    */nu|nu|*/nushell|nushell)
      printf '[install] nushell detected — add to your env.nu manually:\n' >&2
      # shellcheck disable=SC2016
      printf '[install]     $env.PATH = ($env.PATH | prepend "%s")\n' "$bin_dir" >&2
      ;;
  esac

  if [ "$updated_any" -eq 0 ]; then
    return 0
  fi

  # Make openclaw callable in THIS terminal session too (best-effort; the
  # parent shell that ran `curl | bash` is unreachable, but any downstream
  # `openclaw` call inside this script works because run_official_installer
  # already amended PATH).
  printf '[install] run this in your current Terminal to use openclaw now:\n' >&2
  printf '[install]     source %s\n' "$HOME/.zshrc" >&2
  printf '[install] (new Terminal windows will pick it up automatically)\n' >&2
}

open_dashboard() {
  # Launch the Control UI in the user's default browser as the last install
  # step. Best-effort: on headless / SSH / CI boxes the launch may fail, so
  # we absorb the error and print a manual fallback. Opt-out:
  # OPENCLAW_NO_DASHBOARD=1 (mirrors the OPENCLAW_NO_RC_EDIT convention).
  if [ "${OPENCLAW_NO_DASHBOARD:-0}" = "1" ]; then
    printf '[dashboard] OPENCLAW_NO_DASHBOARD=1 — skipping auto-open.\n' >&2
    printf '[dashboard] open manually later with: openclaw dashboard\n' >&2
    return 0
  fi
  printf '[dashboard] opening Control UI in your browser...\n' >&2
  if ! openclaw dashboard; then
    printf '[dashboard] auto-open failed — try running: openclaw dashboard\n' >&2
  fi
}

on_success() {
  printf '\n'
  printf '  [OK] gateway healthy on 127.0.0.1:%s\n' "$PORT"
  printf '  [OK] Telegram bot reachable: @%s\n' "$BOT_USERNAME"
  printf '  [OK] Anthropic API key valid\n'
  printf '\nAll green. Message @%s on Telegram to start chatting.\n' "$BOT_USERNAME"
  printf 'Your OpenClaw Control UI should have opened in your browser.\n'
  printf 'Re-open any time with: openclaw dashboard\n'
  printf '\nWARNING: %s contains your bot token and API key in plaintext (mode 0600).\n' "$OPENCLAW_HOME/openclaw.json"
  printf '         Do not commit, share, or back up unencrypted.\n'
}

main() {
  parse_args "$@"
  # Capture the real install dir BEFORE the dry-run remap clobbers it, so
  # maybe_reset_existing_install probes the user's actual ~/.openclaw
  # rather than the throwaway mktemp dir. Without this, --dry-run --reset
  # would silently report "no config found" on every machine.
  ORIGINAL_OPENCLAW_HOME="$OPENCLAW_HOME"
  if [ "$DRY_RUN" -eq 1 ] && [ -z "${OPENCLAW_HOME_OVERRIDE:-}" ] && [ "$OPENCLAW_HOME" = "$HOME/.openclaw" ]; then
    OPENCLAW_HOME="$(mktemp -d 2>/dev/null || mktemp -d -t openclaw)"
    printf '[dry-run] OPENCLAW_HOME=%s\n' "$OPENCLAW_HOME" >&2
  fi
  preflight
  collect_secrets
  validate_secrets
  maybe_reset_existing_install
  resolve_port
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] skipping official installer\n' >&2
  else
    run_official_installer
    ensure_openclaw_on_path
  fi
  backup_and_write_config
  if [ "$DRY_RUN" -eq 1 ]; then
    install_local_skills
    printf '[dry-run] would restart daemon and verify endpoints\n' >&2
    printf '[dry-run] generated config:\n' >&2
    cat "$OPENCLAW_HOME/openclaw.json"
    return 0
  fi
  start_daemon
  wait_for_healthz
  verify_telegram
  verify_anthropic
  install_local_skills
  open_dashboard
  on_success
}

main "$@"
