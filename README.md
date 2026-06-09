# Claude Code Starter

Shared Claude Code configuration you can fork and customize. Includes skills, agents, hooks, slash commands, and MCP server templates.

## Quick Start

### 1. [Install Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview)

```bash
npm install -g @anthropic-ai/claude-code
```

### 2. Clone this repo

```bash
git clone https://github.com/galorr/claude-code-starter.git
cd claude-code-starter
```

### 3. Run Claude Code

```bash
claude
```

### 4. Paste this prompt

> Set up my Claude Code environment using this repo. Run the install script and help me configure MCP servers (GitHub, Atlassian, Google Drive, BigQuery).

Claude will read the `CLAUDE.md`, run `./install.sh`, walk you through the MCP setup, and get you fully configured.

### 5. Restart Claude Code

Exit and re-open Claude Code to load the new config:

```bash
exit
claude
```

That's it! Try `/go <jira-ticket-url>` to implement your first ticket.

---

## `/go` — One Skill to Rule Them All

The `/go` (aka `/go-devloop`) skill is the primary way to implement Jira tickets. Paste a Jira ticket URL and it handles the full development lifecycle autonomously:

1. **Fetches the Jira ticket** — pulls title, description, acceptance criteria, Figma links, and API contracts
2. **Transitions the ticket** to "In Progress"
3. **Sets up a branch** — asks if you want to stay on the current branch or create a new one (`feat/TICKET-123-...` or `fix/TICKET-123-...`)
4. **Auto-detects UI vs Backend** — classifies the ticket based on labels, description, and linked assets, then routes to the right workflow
5. **Gathers domain context** — for UI tickets: fetches Figma designs; for backend tickets: analyzes existing NestJS modules, DTOs, and entities
6. **Writes an architecture plan** — produces `architecture.md` as the implementation contract
7. **Runs iterative quality loops** — delegates to trycycle for multi-round planning, implementation, testing, and code review (up to 8 review rounds)
8. **Validates the result** — UI tickets get visual QA against Figma; backend tickets get build + test verification
9. **Commits, pushes, and opens a PR** — only after your explicit approval
10. **Handles review comments** — auto-fixes style/formatting feedback from automated reviewers, surfaces logic comments for your approval

### Usage

```
/go https://your-jira.atlassian.net/browse/TICKET-123
```

---

## What's Included

### Skills (23)
Custom skills invoked via `/skill-name` in Claude Code:

#### Development Skills (21)

| Skill | Description |
|-------|-------------|
| `codepilot-be` | Full backend feature dev from Jira ticket (NestJS) |
| `codepilot-ui` | Full frontend feature dev from Jira ticket (Angular) |
| `go-devloop` | Unified dev loop (codepilot + trycycle quality) |
| `trycycle` | Iterative quality improvement loops |
| `webcode` | Pixel-perfect Angular UI from Figma |
| `vibe-coder` | Design-system-aware UI building |
| `output-validator` | Visual QA against Figma specs |
| `frontend-patterns` | Angular patterns and conventions |
| `unit-testing` | Jest unit test generation (NestJS) |
| `ticket-enricher` | Add HLD docs to Jira epics |
| `content-architect` | Blog/LinkedIn content from raw notes |
| `prompt-engineer` | LLM prompt optimization |
| `n8n-builder` | n8n workflow automation |
| `feature-composer` | Feature composition orchestrator |
| `claudia-debugger` | Debug investigator for hard production bugs |
| `knowledge-transfer` | Generate browsable codebase documentation |
| `career-scout` | Career intelligence and interview prep |
| `cp-be` | Shortcut for codepilot-be |
| `cp-ui` | Shortcut for codepilot-ui |
| `go` | Shortcut for go-devloop |
| `kt` | Shortcut for knowledge-transfer |
| `tc` | Shortcut for trycycle |

#### Co-worker Skills (2)

Personal productivity skills designed for daily/weekly automation. Friends can fork, run `/job-scanner-setup`, and get their own personalized instance.

| Skill | Description |
|-------|-------------|
| `job-scanner` | Daily personalized job-market scanner — searches LinkedIn, Glassdoor, VC portfolio boards, remote boards, and a custom watchlist; dedupes against prior runs; verifies every apply link; posts a ranked digest to Slack. Designed for Cowork scheduled tasks. |
| `job-scanner-setup` | Interactive one-time setup for `job-scanner` — reads your CV, asks 5–7 questions, generates a personalized SKILL.md, and optionally registers the daily scheduled task. |

### Slash Commands (16)

| Command | Description |
|---------|-------------|
| `/plan` | Create implementation plan before coding |
| `/code-review` | Review uncommitted changes |
| `/tdd` | Test-driven development |
| `/build-fix` | Fix build/TypeScript errors |
| `/e2e` | Generate & run Playwright E2E tests |
| `/refactor-clean` | Remove dead code safely |
| `/update-docs` | Sync docs with codebase |
| `/verify` | Run comprehensive verification |
| `/checkpoint` | Save progress checkpoint |
| `/learn` | Extract reusable patterns from session |
| `/claudia` | Debug investigation for hard bugs |

### Agents (8)
Specialized sub-agents for parallel task execution — planners, reviewers, debuggers, TDD guides, etc.

### Hooks (7)
Automated quality gates that run during Claude Code sessions:

| Hook | Trigger | Purpose |
|------|---------|---------|
| `hook-quality-gate.js` | PreToolUse | Quality checks before tool execution |
| `hook-ts-typecheck.js` | PostToolUse | TypeScript type checking after edits |
| `hook-autoformat.js` | PostToolUse | Auto-format code after edits |
| `hook-console-log.js` | PostToolUse | Detect leftover console.logs |
| `hook-build-analyzer.js` | PostToolUse | Analyze build output |
| `hook-precompact.js` | PreCompact | Save context before compaction |
| `hook-pattern-extractor.js` | Stop | Extract patterns at session end |

### Scheduled Tasks

Some skills are designed to run automatically on a daily/weekly cron rather than ad-hoc. Scheduling is a [Cowork](https://claude.com) feature (not Claude Code CLI), but the SKILL.md format is identical — install from this repo and register the schedule via Cowork's `/schedule` skill.

| Skill | Suggested schedule | What it does |
|-------|--------------------|--------------|
| `job-scanner` | Daily at 08:00 | Posts a ranked list of NEW openings matching your target role to a Slack channel. See `skills/job-scanner/README.md` for setup. |

To install + schedule in one go: `/job-scanner-setup`

### MCP Servers
Pre-configured templates for stdio servers (saved to `~/.claude/.mcp.json`):
- **GitHub** — requires a Personal Access Token from https://github.com/settings/tokens
- **Atlassian** (Jira/Confluence) — requires your personal API token
- **Google Drive** — requires OAuth credentials

HTTP servers added via `claude mcp add` (saved to `~/.claude.json`):
- **BigQuery** — uses Google's hosted MCP (no credentials needed)

### Local Agents MCP (optional — requires Docker + Ollama)

A fully local, privacy-first MCP server powered by a local LLM (Ollama). No data leaves your machine.

| Tool | What it does |
|------|-------------|
| `codebase_qa` | Ask any repo a question — get a cited answer from a local LLM |
| `explore` | Deep repo exploration with shared vector memory across sessions |
| `explore_lite` | Lightweight file exploration — no memory needed, instant |
| `git_yoda` | Natural-language git/gh operations (dry-run by default) |
| `pr_desc` | Generate a structured PR description (What/Why/How to Test/Risks) |
| `save_handover` | Write a handover note so a fresh session can resume |
| `latest_handover` | Retrieve the most recent handover for a project |
| `memory_remember` | Store a durable note or decision in shared vector memory |
| `memory_recall` | Semantic search over all stored memories |

**Prerequisites:** Docker, Ollama (`ollama pull qwen3-coder:30b` + `ollama pull nomic-embed-text`), Python 3.11+

The installer sets up a Python venv, starts MongoDB via Docker, and registers the MCP in both Claude Code and Claude Desktop. Memory is **optional** — all file tools work without MongoDB/Ollama.

## Using the Local Agents MCP in Claude Code

Two steps are needed: **registering** the server so Claude Code loads it, and **documenting** it so Claude knows when to use it.

### Step 1 — Register the server

Run `./install.sh` and answer **Y** to the local-agents question. It will:
- Create a Python venv inside `local-agents/`
- Start MongoDB via Docker
- Patch `~/.claude.json` with the MCP entry (user-scoped — available in every project)
- Pull the required Ollama models

Then **restart Claude Code**.

> **Project-scoped alternative:** If you only want the MCP in one repo, put the entry in a `.mcp.json` file at that repo's root — Claude Code reads it automatically without touching `~/.claude.json`.

### Step 2 — Tell Claude when to use it (`CLAUDE.md`)

Registering makes the tools *callable*, but Claude won't reach for them unprompted. The `CLAUDE.md` in this repo already contains a usage table that ships to `~/.claude/` on install:

| Situation | Tool |
|-----------|------|
| "How does X work in this codebase?" | `explore_lite` — fast, no memory needed |
| Deep investigation spanning many files | `explore` — uses shared memory, resumable |
| Recurring Q&A about a repo | `codebase_qa` — cited answers, auto-saved to memory |
| Any git/GitHub task in plain English | `git_yoda` — dry-run by default |
| Writing a PR description | `pr_desc` — generates What/Why/How to Test/Risks |
| Saving a decision for future sessions | `memory_remember` |
| Recalling prior work | `memory_recall` |
| Ending a long session | `save_handover` |
| Resuming a prior session | `explore(resume=true)` |

All tools degrade gracefully — if the server is not running or Ollama/MongoDB is unavailable, Claude falls back to normal file tools.

---

## Gotcha: Trycycle and nested Claude Code sessions

If you invoke `trycycle` (directly, via `/tc`, or through `/go` → `go-devloop`)
from inside Claude Code and see:

> Trycycle cannot nest Claude Code sessions in this environment

...it means trycycle tried to use its fallback runner
(`orchestrator/subagent_runner.py`), which spawns `claude -p ...` as a
subprocess. The Claude Code CLI refuses to launch inside an active session
because nested sessions share runtime resources and will crash each other.

**Fix:** trycycle must use *native* transport in Claude Code — i.e. the
built-in `Task` tool — not the fallback runner. `CLAUDE.md` in this repo
now tells Claude exactly that, so a restarted session will pick it up
automatically. If you still see the error, paste this directive when
invoking trycycle:

> Use trycycle to \<task\>. Transport: native only. Dispatch every trycycle
> subagent via the Claude Code Task tool (subagent_type: general-purpose),
> and resume persistent ones via the Task tool's `resume` parameter. Do NOT
> invoke `subagent_runner.py`. If native dispatch is not possible, stop
> and tell me instead of falling back.

## Updating

Pull the latest and re-run Claude:

```bash
cd claude-code-starter
git pull --recurse-submodules
claude
```

> Update my Claude Code environment from this repo.

## MCP Setup (Manual)

If you skipped MCP during install, copy the template and fill in your secrets:

```bash
cp mcp-servers.json.template ~/.claude/.mcp.json
# Edit ~/.claude/.mcp.json and replace placeholders:
#   __YOUR_GITHUB_PAT__
#   __YOUR_ATLASSIAN_EMAIL__
#   __YOUR_ATLASSIAN_API_TOKEN__
#   __GOOGLE_DRIVE_OAUTH_CREDENTIALS_PATH__
```

- Get your GitHub PAT at: https://github.com/settings/tokens
- Get your Atlassian API token at: https://id.atlassian.com/manage-profile/security/api-tokens

## Backup & Restore

The installer automatically backs up your existing config to `~/.claude/backups/pre-team-setup-<timestamp>/`. To restore:

```bash
cp -R ~/.claude/backups/pre-team-setup-<timestamp>/* ~/.claude/
```
