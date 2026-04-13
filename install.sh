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

PORT="$DEFAULT_PORT"
DRY_RUN=0
BOT_USERNAME=""

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: install.sh [--port N] [--dry-run] [--help]

Options:
  --port N       Gateway port to write into openclaw.json (default 18789)
  --dry-run      Collect inputs and show generated config; skip installer + daemon
  --help, -h     Show this message

Environment:
  TELEGRAM_BOT_TOKEN     If set, skip interactive prompt
  ANTHROPIC_API_KEY      If set, skip interactive prompt
  OPENCLAW_INSTALL_URL   Override official installer URL
  OPENCLAW_HOME          Override install dir (default: $HOME/.openclaw)
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
        shift 2
        ;;
      --port=*)
        PORT="${1#--port=}"
        shift
        ;;
      --dry-run)
        DRY_RUN=1
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

preflight() {
  local os
  os="$(detect_os)"

  local jq_hint curl_hint
  if [ "$os" = "Darwin" ]; then
    jq_hint="install with: brew install jq"
    curl_hint="install with: brew install curl"
  else
    jq_hint="install with: sudo apt install jq (or your distro equivalent)"
    curl_hint="install with: sudo apt install curl (or your distro equivalent)"
  fi

  require_cmd curl "$curl_hint"
  require_cmd jq "$jq_hint"

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

run_official_installer() {
  local url="${OPENCLAW_INSTALL_URL:-$DEFAULT_INSTALL_URL}"
  printf '[install] fetching %s\n' "$url" >&2
  # pipefail ensures a curl failure propagates even through the pipe to bash.
  curl -fsSL --proto '=https' --tlsv1.2 --max-time 30 "$url" | bash \
    || die "official installer failed (url: $url)"

  command -v openclaw >/dev/null 2>&1 \
    || die "openclaw not on PATH after install — check installer output above"
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

on_success() {
  printf '\n'
  printf '  [OK] gateway healthy on 127.0.0.1:%s\n' "$PORT"
  printf '  [OK] Telegram bot reachable: @%s\n' "$BOT_USERNAME"
  printf '  [OK] Anthropic API key valid\n'
  printf '\nAll green. Message @%s on Telegram to start chatting.\n' "$BOT_USERNAME"
  printf '\nWARNING: %s contains your bot token and API key in plaintext (mode 0600).\n' "$OPENCLAW_HOME/openclaw.json"
  printf '         Do not commit, share, or back up unencrypted.\n'
}

main() {
  parse_args "$@"
  if [ "$DRY_RUN" -eq 1 ] && [ -z "${OPENCLAW_HOME_OVERRIDE:-}" ] && [ "$OPENCLAW_HOME" = "$HOME/.openclaw" ]; then
    OPENCLAW_HOME="$(mktemp -d 2>/dev/null || mktemp -d -t openclaw)"
    printf '[dry-run] OPENCLAW_HOME=%s\n' "$OPENCLAW_HOME" >&2
  fi
  preflight
  collect_secrets
  validate_secrets
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] skipping official installer\n' >&2
  else
    run_official_installer
  fi
  backup_and_write_config
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] would restart daemon and verify endpoints\n' >&2
    printf '[dry-run] generated config:\n' >&2
    cat "$OPENCLAW_HOME/openclaw.json"
    return 0
  fi
  start_daemon
  wait_for_healthz
  verify_telegram
  verify_anthropic
  on_success
}

main "$@"
