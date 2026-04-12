#!/usr/bin/env bash
# install-skill.sh — install OpenClaw skills from the public toolkit tarball
# into ~/.openclaw/skills/<name>/. Picked up by the gateway on next agent turn
# (skills.load.watch defaults on; no daemon restart needed).
#
# Usage:
#   curl -fsSL .../install-skill.sh | bash                   # install all
#   curl -fsSL .../install-skill.sh | bash -s content-monitor
#   ./install-skill.sh --dry-run                             # show, don't write
#
# Overwrites any existing ~/.openclaw/skills/<name>/ — do not hand-edit files there.
# Bash 3.2 compatible (stock macOS). Requires: curl, tar.

set -euo pipefail
IFS=$'\n\t'

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"
DEFAULT_TARBALL_URL="https://github.com/xuantinfx/openclaw-install-toolkit/archive/refs/heads/main.tar.gz"
TOOLKIT_TARBALL_URL="${TOOLKIT_TARBALL_URL:-$DEFAULT_TARBALL_URL}"

SKILLS=()
DRY_RUN=0
TMPDIR_INSTALL=""

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: install-skill.sh [--dry-run] [--help] [skill ...]

Fetches the public OpenClaw toolkit tarball and installs the requested skills
into ~/.openclaw/skills/<name>/. With no skill args, installs every skill
shipped in the tarball.

Options:
  --dry-run      Fetch + list what would be installed; no writes to ~/.openclaw
  --help, -h     Show this message

Environment:
  OPENCLAW_HOME            Override install root (default: $HOME/.openclaw)
  TOOLKIT_TARBALL_URL      Override tarball source (default: public toolkit main)
  TOOLKIT_ALLOW_INSECURE   CI-only: allow http/file tarball URLs (never in prod)

Notes:
  - Any existing ~/.openclaw/skills/<name>/ is replaced wholesale.
  - Run install.sh first — this script refuses to run without ~/.openclaw/.
EOF
}

cleanup() {
  if [ -n "$TMPDIR_INSTALL" ] && [ -d "$TMPDIR_INSTALL" ]; then
    rm -rf "$TMPDIR_INSTALL"
  fi
}
trap cleanup EXIT

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --dry-run) DRY_RUN=1; shift ;;
      -h|--help) usage; exit 0 ;;
      --) shift; while [ $# -gt 0 ]; do SKILLS+=("$1"); shift; done ;;
      --*) usage >&2; die "unknown flag: $1" ;;
      *) SKILLS+=("$1"); shift ;;
    esac
  done
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

# Reject anything that could path-traverse or shell-surprise us.
# Skill names must match OpenClaw's skill-id convention: lowercase alnum + `_-`.
validate_skill_name() {
  local name="$1"
  case "$name" in
    ''|.|..|*/*|*\\*|.*) die "invalid skill name: '$name'" ;;
  esac
  printf '%s' "$name" | grep -Eq '^[a-z0-9][a-z0-9_-]{0,63}$' \
    || die "invalid skill name: '$name' (must match [a-z0-9][a-z0-9_-]{0,63})"
}

preflight() {
  require_cmd curl
  require_cmd tar
  [ -d "$OPENCLAW_HOME" ] \
    || die "$OPENCLAW_HOME not found — run install.sh first"
}

fetch_tarball() {
  TMPDIR_INSTALL="$(mktemp -d 2>/dev/null || mktemp -d -t openclaw-skill)"
  printf '[fetch] %s\n' "$TOOLKIT_TARBALL_URL" >&2
  # Lock transport to HTTPS+TLS1.2. `TOOLKIT_ALLOW_INSECURE=1` relaxes this
  # to http/file for local CI smoke tests only — never set in production.
  local curl_protos='=https'
  if [ -n "${TOOLKIT_ALLOW_INSECURE:-}" ]; then
    # file:// only (for local CI fixtures); keep https in the list so a relaxed
    # CI run that happens to hit a real URL still works.
    curl_protos='=https,file'
  fi
  curl -fsSL --proto "$curl_protos" --tlsv1.2 --max-time 60 "$TOOLKIT_TARBALL_URL" \
    | tar -xz -C "$TMPDIR_INSTALL" \
    || die "failed to fetch/extract toolkit tarball ($TOOLKIT_TARBALL_URL)"

  # Reject symlinks anywhere in the extracted tree — a compromised upstream
  # could smuggle one pointing at /etc/* and `cp -R` would dereference it.
  if find "$TMPDIR_INSTALL" -type l | read -r; then
    die "tarball contains symlinks; refusing to install (possible tampering)"
  fi

  # Extracted archive has exactly one top-level dir (e.g., openclaw-install-toolkit-main/).
  # Assert that instead of blindly `head -1`ing, so a reshaped tarball fails loudly.
  local count root
  count="$(find "$TMPDIR_INSTALL" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
  [ "$count" = "1" ] \
    || die "tarball has $count top-level directories (expected 1) — wrong URL?"
  root="$(find "$TMPDIR_INSTALL" -mindepth 1 -maxdepth 1 -type d)"
  [ -d "$root/skills" ] || die "tarball has no skills/ directory — wrong URL?"
  TARBALL_ROOT="$root"
}

enumerate_skills() {
  if [ "${#SKILLS[@]}" -eq 0 ]; then
    local entry name
    for entry in "$TARBALL_ROOT/skills"/*/; do
      [ -d "$entry" ] || continue
      name="$(basename "$entry")"
      SKILLS+=("$name")
    done
  fi
  [ "${#SKILLS[@]}" -gt 0 ] || die "no skills found in tarball"
}

install_one() {
  local skill="$1"
  validate_skill_name "$skill"
  local src="$TARBALL_ROOT/skills/$skill"
  local dst="$OPENCLAW_HOME/skills/$skill"

  [ -d "$src" ] || die "skill not in toolkit: $skill"
  [ -f "$src/SKILL.md" ] \
    || die "skill '$skill' is missing SKILL.md at its root — corrupt toolkit?"

  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] would install %s -> %s\n' "$skill" "$dst" >&2
    return 0
  fi

  mkdir -p "$OPENCLAW_HOME/skills" || die "cannot create $OPENCLAW_HOME/skills"
  rm -rf "$dst"
  cp -R "$src" "$dst" || die "failed to copy $skill into place"
  printf '[install] %s -> %s\n' "$skill" "$dst" >&2
}

main() {
  parse_args "$@"
  preflight
  fetch_tarball
  enumerate_skills

  local skill
  for skill in "${SKILLS[@]}"; do
    install_one "$skill"
  done

  printf '\n'
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] %d skill(s) would be installed. No changes made.\n' "${#SKILLS[@]}"
  else
    printf '[done] installed %d skill(s) into %s/skills/\n' "${#SKILLS[@]}" "$OPENCLAW_HOME"
    printf '       gateway picks these up on the next agent turn (no restart needed).\n'
  fi
}

main "$@"
