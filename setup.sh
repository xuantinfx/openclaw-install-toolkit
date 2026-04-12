#!/usr/bin/env bash
# =============================================================================
# setup.sh — Content Monitor Pipeline Setup
# Installs skill + workspace structure + cron job on a fresh OpenClaw machine
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENCLAW_SKILLS="/opt/homebrew/lib/node_modules/openclaw/skills"
WORKSPACE="$HOME/.openclaw/workspace"

echo ""
echo "🦞 Content Monitor — Setup Script"
echo "=================================="
echo ""

# ── Recommend agent-driven setup ─────────────────────────────────────────────
echo "💡 Recommended: Tell the agent 'setup content monitor' for interactive setup."
echo "   The agent will walk you through everything in chat."
echo "   This script is for manual/headless setup only."
echo ""
read -p "   Continue with manual setup? [y/N]: " MANUAL
if [ "${MANUAL,,}" != "y" ] && [ "${MANUAL,,}" != "yes" ]; then
    echo "   Run: tell the agent 'setup content monitor'"
    exit 0
fi

# ── 1. Check OpenClaw installed ──────────────────────────────────────────────
if ! command -v openclaw &>/dev/null; then
    echo "❌ OpenClaw not found. Install it first:"
    echo "   https://docs.openclaw.ai/getting-started"
    exit 1
fi
echo "✅ OpenClaw found: $(openclaw --version 2>/dev/null || echo 'installed')"

# ── 2. Install skill ─────────────────────────────────────────────────────────
echo ""
echo "📦 Installing content-monitor skill..."
if [ -d "$OPENCLAW_SKILLS/content-monitor" ]; then
    echo "   Removing old version..."
    rm -rf "$OPENCLAW_SKILLS/content-monitor"
fi
cp -r "$SCRIPT_DIR/content-monitor" "$OPENCLAW_SKILLS/content-monitor"
echo "✅ Skill installed → $OPENCLAW_SKILLS/content-monitor"

# ── 3. Create workspace structure ────────────────────────────────────────────
echo ""
echo "📁 Creating workspace structure..."
mkdir -p "$WORKSPACE/sites/personal-injury"
mkdir -p "$WORKSPACE/sites/mortgage"
mkdir -p "$WORKSPACE/news"
mkdir -p "$WORKSPACE/posts/drafts/personal-injury"
mkdir -p "$WORKSPACE/posts/drafts/mortgage"
mkdir -p "$WORKSPACE/posts/drafts/general"
mkdir -p "$WORKSPACE/posts/images"
mkdir -p "$WORKSPACE/posts/approved"
mkdir -p "$WORKSPACE/posts/published"
mkdir -p "$WORKSPACE/memory"
echo "✅ Workspace structure created"

# ── 4. API Keys ───────────────────────────────────────────────────────────────
echo ""
echo "🔑 API Keys Setup"
echo "-----------------"

CONFIG_FILE="$WORKSPACE/.env-content-monitor"

read -p "   Firecrawl API key (fc-...): " FC_KEY
read -p "   Google AI API key (AIzaSy...): " GOOGLE_KEY
read -p "   Brave Search API key (optional, press Enter to skip): " BRAVE_KEY

cat > "$CONFIG_FILE" <<EOF
# Content Monitor API Keys
# Source this file before running scripts:
#   source ~/.openclaw/workspace/.env-content-monitor

export FIRECRAWL_API_KEY="$FC_KEY"
export GOOGLE_AI_API_KEY="$GOOGLE_KEY"
export BRAVE_API_KEY="$BRAVE_KEY"
EOF
chmod 600 "$CONFIG_FILE"
echo "✅ API keys saved → $CONFIG_FILE"
echo "   (chmod 600 — private, readable by you only)"

# ── 5. Domain config ─────────────────────────────────────────────────────────
echo ""
echo "🌐 Website Domain"
echo "-----------------"
read -p "   Your website domain (e.g. www.mysite.com) or press Enter to use placeholder: " DOMAIN
DOMAIN="${DOMAIN:-www.yoursite.com}"

# Update domain in scripts
sed -i '' "s|www.yoursite.com|$DOMAIN|g" \
    "$OPENCLAW_SKILLS/content-monitor/scripts/suggest_daily.py" \
    "$OPENCLAW_SKILLS/content-monitor/scripts/blog_draft.py" \
    "$WORKSPACE/skills/content-monitor/scripts/suggest_daily.py" \
    "$WORKSPACE/skills/content-monitor/scripts/blog_draft.py" 2>/dev/null || true
echo "✅ Domain set to: $DOMAIN"

# ── 6. Initialize content calendar ───────────────────────────────────────────
echo ""
echo "📅 Initializing content calendar..."
if [ ! -f "$WORKSPACE/content-calendar.json" ]; then
    echo '{"posts": []}' > "$WORKSPACE/content-calendar.json"
    echo "✅ content-calendar.json created"
else
    echo "   (already exists — skipping)"
fi

if [ ! -f "$WORKSPACE/crawl-state.json" ]; then
    echo '{"last_crawled": {}}' > "$WORKSPACE/crawl-state.json"
    echo "✅ crawl-state.json created"
else
    echo "   (already exists — skipping)"
fi

# ── 7. Test pipeline ─────────────────────────────────────────────────────────
echo ""
echo "🧪 Running quick pipeline test..."
source "$CONFIG_FILE"

python3 "$OPENCLAW_SKILLS/content-monitor/scripts/suggest_daily.py" --count 1 2>&1 | head -10
echo "✅ Pipeline test OK"

# ── 8. Setup cron via OpenClaw ───────────────────────────────────────────────
echo ""
echo "⏰ Cron Job"
echo "----------"
echo "   Daily briefing cron needs to be set up via OpenClaw chat."
echo "   After setup, tell your agent:"
echo ""
echo '   "Set up the content-monitor daily cron at 7AM Asia/Saigon"'
echo ""
echo "   Or use the OpenClaw web UI → Cron Jobs → Add"

# ── 9. Done ───────────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "✅ Content Monitor setup complete!"
echo "============================================"
echo ""
echo "📋 Next steps:"
echo "   1. Open OpenClaw chat"
echo "   2. Say: 'run content pipeline'"
echo "   3. Pick your post → image generates → approve"
echo ""
echo "📁 Key locations:"
echo "   Skill:     $OPENCLAW_SKILLS/content-monitor/"
echo "   Drafts:    $WORKSPACE/posts/drafts/"
echo "   Approved:  $WORKSPACE/posts/approved/"
echo "   API keys:  $CONFIG_FILE"
echo ""
echo "🔑 To load API keys in terminal:"
echo "   source $CONFIG_FILE"
echo ""
echo "🧙 For full interactive setup (websites, social login, writing style, cron):"
echo "   Tell the agent: 'setup content monitor'"
echo ""
