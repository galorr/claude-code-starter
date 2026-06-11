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

COMPONENTS=(commands skills agents hooks scheduled settings.json .mcp.json)
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

info "Installing scheduled tasks..."
rm -rf "$CLAUDE_DIR/scheduled"
cp -R "$SCRIPT_DIR/scheduled" "$CLAUDE_DIR/scheduled"
ok "Scheduled tasks installed ($(ls "$CLAUDE_DIR/scheduled"/*.task.md 2>/dev/null | wc -l | tr -d ' ') tasks)"

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

# ── Local Agents MCP (Ollama + MongoDB) ────

echo ""
echo "──────────────────────────────────────────"
echo "  Local Agents MCP (optional)"
echo "  Runs a local LLM (Ollama) to power:"
echo "    codebase_qa  explore  explore_lite"
echo "    git_yoda     pr_desc  memory"
echo "──────────────────────────────────────────"
echo ""
echo -n "Set up local-agents MCP (requires Docker + Ollama)? [Y/n]: "
read -r SETUP_LOCAL_AGENTS

if [[ ! "$SETUP_LOCAL_AGENTS" =~ ^[Nn]$ ]]; then
  LOCAL_AGENTS_DIR="$SCRIPT_DIR/local-agents"
  VENV="$LOCAL_AGENTS_DIR/.venv"

  # Python venv
  if ! command -v python3 &>/dev/null; then
    warn "python3 not found — skipping local-agents setup"
  else
    info "Creating Python venv at $VENV..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet "mcp[cli]" pymongo
    ok "Python venv ready"

    # MongoDB via Docker
    if command -v docker &>/dev/null && (docker compose version &>/dev/null 2>&1 || docker-compose version &>/dev/null 2>&1); then
      info "Starting MongoDB (docker compose)..."
      COMPOSE_CMD="docker compose"
      docker compose version &>/dev/null 2>&1 || COMPOSE_CMD="docker-compose"
      (cd "$LOCAL_AGENTS_DIR" && $COMPOSE_CMD up -d)
      ok "MongoDB started"
      MONGO_URI="mongodb://user:password@127.0.0.1:27017/agent_memory?authSource=admin&directConnection=true"
    else
      warn "Docker not found — MongoDB not started. Memory features will be unavailable."
      MONGO_URI=""
    fi

    # Patch Claude Code config (~/.claude.json)
    info "Registering local-agents in Claude Code (~/.claude.json)..."
    CLAUDE_JSON="$HOME/.claude.json"
    [ -f "$CLAUDE_JSON" ] || python3 -c "import json; json.dump({}, open('$CLAUDE_JSON','w'))"
    python3 - "$CLAUDE_JSON" "$VENV/bin/python3" "$LOCAL_AGENTS_DIR/mcp/server.py" "$MONGO_URI" <<'PYEOF'
import json, sys
cfg_file, venv_py, srv_py, mongo_uri = sys.argv[1:]
with open(cfg_file) as f:
    cfg = json.load(f)
cfg.setdefault("mcpServers", {})
entry = {"command": venv_py, "args": [srv_py], "env": {
    "MEMORY_VECTOR_MODE": "bruteforce",
    "MEMORY_EMBED_MODEL": "nomic-embed-text",
    "MEMORY_EMBED_DIMS": "768",
    "LOCAL_AGENT_MODEL": "qwen3-coder:30b",
    "CODEBASE_QA_MODEL": "qwen3-coder:30b",
    "GIT_YODA_MODEL": "qwen3-coder:30b",
    "PR_DESC_MODEL": "qwen3-coder:30b",
}}
if mongo_uri:
    entry["env"]["MONGODB_URI"] = mongo_uri
cfg["mcpServers"]["local-agents"] = entry
with open(cfg_file, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
PYEOF
    ok "Registered in ~/.claude.json"

    # Patch Claude Desktop config
    DESKTOP_CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
    if [ -d "$HOME/Library/Application Support/Claude" ]; then
      info "Registering local-agents in Claude Desktop..."
      [ -f "$DESKTOP_CFG" ] || python3 -c "import json; json.dump({}, open('$DESKTOP_CFG','w'))"
      python3 - "$DESKTOP_CFG" "$VENV/bin/python3" "$LOCAL_AGENTS_DIR/mcp/server.py" "$MONGO_URI" <<'PYEOF'
import json, sys
cfg_file, venv_py, srv_py, mongo_uri = sys.argv[1:]
with open(cfg_file) as f:
    cfg = json.load(f)
cfg.setdefault("mcpServers", {})
entry = {"command": venv_py, "args": [srv_py], "env": {
    "MEMORY_VECTOR_MODE": "bruteforce",
    "MEMORY_EMBED_MODEL": "nomic-embed-text",
    "MEMORY_EMBED_DIMS": "768",
    "LOCAL_AGENT_MODEL": "qwen3-coder:30b",
    "CODEBASE_QA_MODEL": "qwen3-coder:30b",
    "GIT_YODA_MODEL": "qwen3-coder:30b",
    "PR_DESC_MODEL": "qwen3-coder:30b",
}}
if mongo_uri:
    entry["env"]["MONGODB_URI"] = mongo_uri
cfg["mcpServers"]["local-agents"] = entry
with open(cfg_file, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
PYEOF
      ok "Registered in Claude Desktop"
    fi

    # Ollama models
    if command -v ollama &>/dev/null && curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
      info "Pulling Ollama models (this may take a while)..."
      ollama pull nomic-embed-text && ok "nomic-embed-text ready"
      ollama pull qwen3-coder:30b  && ok "qwen3-coder:30b ready"
    else
      warn "Ollama not running. After starting Ollama, run:"
      warn "  ollama pull nomic-embed-text"
      warn "  ollama pull qwen3-coder:30b"
    fi

    # git pr-desc alias
    git config --global alias.pr-desc "!python3 $LOCAL_AGENTS_DIR/scripts/pr_desc.py"
    ok "git pr-desc alias registered"
  fi
else
  info "Skipping local-agents setup."
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
echo "  Scheduled: $(ls "$CLAUDE_DIR/scheduled"/*.task.md 2>/dev/null | wc -l | tr -d ' ') task definitions"
echo ""

if [ -f "$CLAUDE_DIR/.mcp.json" ]; then
  echo "  MCP Servers (cloud): configured"
else
  echo "  MCP Servers (cloud): not configured (run install.sh again to set up)"
fi

if [ -f "$HOME/.claude.json" ] && python3 -c "import json; d=json.load(open('$HOME/.claude.json')); exit(0 if 'local-agents' in d.get('mcpServers',{}) else 1)" 2>/dev/null; then
  echo "  Local Agents MCP:    configured (codebase_qa, explore, git_yoda, pr_desc, memory)"
else
  echo "  Local Agents MCP:    not configured (run install.sh again to set up)"
fi

echo ""
ok "Installation complete! Start a new Claude Code session to use the new config."
echo ""
echo "  Useful commands to try:"
echo "    /plan          - Plan before coding"
echo "    /code-review   - Review uncommitted changes"
echo "    /tdd           - Test-driven development"
echo "    /build-fix     - Fix build errors"
echo "    codebase_qa    - Ask any repo a question (via local-agents MCP)"
echo "    git pr-desc    - Generate a PR description from your diff"
echo ""
