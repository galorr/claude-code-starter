#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# Claude Code Team Setup - Install Script
# ──────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
BACKUP_DIR="$CLAUDE_DIR/backups/pre-team-setup-$(date +%Y%m%d-%H%M%S)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Pre-checks ──────────────────────────────

if ! command -v claude &>/dev/null; then
  error "Claude Code CLI not found. Install it first: https://docs.anthropic.com/en/docs/claude-code"
  exit 1
fi

if ! command -v node &>/dev/null; then
  error "Node.js not found. Install Node.js 18+ first."
  exit 1
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Claude Code Team Setup Installer       ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Init submodules (trycycle) ──────────────

info "Initializing git submodules (trycycle)..."
cd "$SCRIPT_DIR"
git submodule update --init --recursive
ok "Submodules ready"

# ── Backup existing config ──────────────────

COMPONENTS=(commands skills agents hooks settings.json .mcp.json)
HAS_EXISTING=false

for item in "${COMPONENTS[@]}"; do
  if [ -e "$CLAUDE_DIR/$item" ]; then
    HAS_EXISTING=true
    break
  fi
done

if $HAS_EXISTING; then
  warn "Found existing Claude Code config. Creating backup..."
  mkdir -p "$BACKUP_DIR"
  for item in "${COMPONENTS[@]}"; do
    if [ -e "$CLAUDE_DIR/$item" ]; then
      cp -R "$CLAUDE_DIR/$item" "$BACKUP_DIR/"
    fi
  done
  ok "Backup saved to: $BACKUP_DIR"
else
  info "No existing config found, skipping backup."
fi

# ── Ensure ~/.claude exists ─────────────────

mkdir -p "$CLAUDE_DIR"

# ── Copy components ─────────────────────────

info "Installing commands (slash commands)..."
rm -rf "$CLAUDE_DIR/commands"
cp -R "$SCRIPT_DIR/commands" "$CLAUDE_DIR/commands"
ok "Commands installed ($(ls "$CLAUDE_DIR/commands" | wc -l | tr -d ' ') items)"

info "Installing skills..."
rm -rf "$CLAUDE_DIR/skills"
cp -R "$SCRIPT_DIR/skills" "$CLAUDE_DIR/skills"
ok "Skills installed ($(ls "$CLAUDE_DIR/skills" | wc -l | tr -d ' ') skills)"

info "Installing agents..."
rm -rf "$CLAUDE_DIR/agents"
cp -R "$SCRIPT_DIR/agents" "$CLAUDE_DIR/agents"
ok "Agents installed ($(ls "$CLAUDE_DIR/agents" | wc -l | tr -d ' ') agents)"

info "Installing hooks..."
rm -rf "$CLAUDE_DIR/hooks"
cp -R "$SCRIPT_DIR/hooks" "$CLAUDE_DIR/hooks"
ok "Hooks installed ($(ls "$CLAUDE_DIR/hooks" | wc -l | tr -d ' ') hooks)"

info "Installing settings.json..."
if [ -f "$CLAUDE_DIR/settings.json" ]; then
  warn "Existing settings.json found — merging hooks only would be complex."
  echo -n "  Overwrite settings.json with team config? [y/N]: "
  read -r OVERWRITE_SETTINGS
  if [[ "$OVERWRITE_SETTINGS" =~ ^[Yy]$ ]]; then
    cp "$SCRIPT_DIR/settings.json" "$CLAUDE_DIR/settings.json"
    ok "Settings installed"
  else
    warn "Skipped settings.json (kept existing)"
  fi
else
  cp "$SCRIPT_DIR/settings.json" "$CLAUDE_DIR/settings.json"
  ok "Settings installed"
fi

info "Installing package.json & running npm install..."
cp "$SCRIPT_DIR/package.json" "$CLAUDE_DIR/package.json"
(cd "$CLAUDE_DIR" && npm install --silent 2>/dev/null) || warn "npm install had issues — you may need to run it manually"
ok "Dependencies installed"

# ── MCP Server Configuration ───────────────

echo ""
echo "──────────────────────────────────────────"
echo "  MCP Server Configuration (optional)"
echo "──────────────────────────────────────────"
echo ""

echo -n "Configure MCP servers (GitHub, Atlassian, Google Drive) and add HTTP servers (BigQuery)? [Y/n]: "
read -r CONFIGURE_MCP

if [[ ! "$CONFIGURE_MCP" =~ ^[Nn]$ ]]; then
  cp "$SCRIPT_DIR/mcp-servers.json.template" /tmp/_mcp_template.json

  # GitHub
  echo ""
  info "GitHub MCP setup:"
  echo "  Generate a token at: https://github.com/settings/tokens"
  echo -n "  Your GitHub Personal Access Token (or press Enter to skip): "
  read -rs GITHUB_PAT
  echo ""

  if [ -n "$GITHUB_PAT" ]; then
    sed -i'' -e "s|__YOUR_GITHUB_PAT__|$GITHUB_PAT|g" /tmp/_mcp_template.json
    ok "GitHub configured"
  else
    warn "Skipped GitHub"
  fi

  # Atlassian
  echo ""
  info "Atlassian (Jira/Confluence) setup:"
  echo "  Generate a token at: https://id.atlassian.com/manage-profile/security/api-tokens"
  echo -n "  Your Atlassian base URL (e.g. https://your-org.atlassian.net): "
  read -r ATLASSIAN_URL
  echo -n "  Your Atlassian account email: "
  read -r ATLASSIAN_EMAIL
  echo -n "  Your Atlassian API token: "
  read -rs ATLASSIAN_TOKEN
  echo ""

  if [ -n "$ATLASSIAN_URL" ] && [ -n "$ATLASSIAN_EMAIL" ] && [ -n "$ATLASSIAN_TOKEN" ]; then
    sed -i'' -e "s|__YOUR_ATLASSIAN_BASE_URL__|$ATLASSIAN_URL|g" /tmp/_mcp_template.json
    sed -i'' -e "s|__YOUR_EMAIL__|$ATLASSIAN_EMAIL|g" /tmp/_mcp_template.json
    sed -i'' -e "s|__YOUR_ATLASSIAN_API_TOKEN__|$ATLASSIAN_TOKEN|g" /tmp/_mcp_template.json
    ok "Atlassian configured"
  else
    warn "Skipped Atlassian (empty input)"
  fi

  # Google Drive
  echo ""
  info "Google Drive MCP setup:"
  echo "  You need OAuth credentials JSON from Google Cloud Console."
  echo -n "  Path to your Google Drive OAuth credentials JSON (or press Enter to skip): "
  read -r GDRIVE_CREDS

  if [ -n "$GDRIVE_CREDS" ]; then
    sed -i'' -e "s|__GOOGLE_DRIVE_OAUTH_CREDENTIALS_PATH__|$GDRIVE_CREDS|g" /tmp/_mcp_template.json
    ok "Google Drive configured"
  else
    # Remove google-drive entry if skipped
    warn "Skipped Google Drive"
  fi

  cp /tmp/_mcp_template.json "$CLAUDE_DIR/.mcp.json"
  rm -f /tmp/_mcp_template.json /tmp/_mcp_template.json-e
  ok "Stdio MCP servers saved to ~/.claude/.mcp.json"

  # HTTP MCP servers must be added via `claude mcp add` (user-level config)
  # because Claude Code reads HTTP servers from ~/.claude.json, not .mcp.json
  info "Adding HTTP MCP servers (BigQuery)..."
  if ! err=$(claude mcp add --transport http -s user bigquery "https://bigquery.googleapis.com/mcp" 2>&1); then
    warn "Failed to add BigQuery MCP: $err"
  else
    ok "BigQuery MCP added"
  fi
else
  info "Skipping MCP configuration. You can set it up later by running install.sh again."
fi

# ── Verify installation ────────────────────

echo ""
echo "──────────────────────────────────────────"
echo "  Installation Summary"
echo "──────────────────────────────────────────"
echo ""

echo "  Commands:  $(ls "$CLAUDE_DIR/commands"/*.md 2>/dev/null | wc -l | tr -d ' ') commands + $(ls -d "$CLAUDE_DIR/commands"/*/ 2>/dev/null | wc -l | tr -d ' ') command groups"
echo "  Skills:    $(ls -d "$CLAUDE_DIR/skills"/*/ 2>/dev/null | wc -l | tr -d ' ') skills"
echo "  Agents:    $(ls "$CLAUDE_DIR/agents"/*.md 2>/dev/null | wc -l | tr -d ' ') agents"
echo "  Hooks:     $(ls "$CLAUDE_DIR/hooks"/*.js 2>/dev/null | wc -l | tr -d ' ') hooks"
echo ""

if [ -f "$CLAUDE_DIR/.mcp.json" ]; then
  echo "  MCP Servers: configured"
else
  echo "  MCP Servers: not configured (run install.sh again to set up)"
fi

echo ""
ok "Installation complete! Start a new Claude Code session to use the new config."
echo ""
echo "  Useful commands to try:"
echo "    /plan          - Plan before coding"
echo "    /code-review   - Review uncommitted changes"
echo "    /tdd           - Test-driven development"
echo "    /build-fix     - Fix build errors"
echo ""
