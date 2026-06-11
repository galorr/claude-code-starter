# Claude Code Starter Setup

This repo contains shared Claude Code configuration. When a user asks you to set up their environment, run the install script and help them configure MCP servers.

## Setup Instructions

When the user asks to install or set up their Claude Code environment using this repo:

1. **Run the install script:**
   ```bash
   ./install.sh
   ```
   This backs up existing config, copies all components (commands, skills, agents, hooks, scheduled tasks, settings) into `~/.claude/`, and runs `npm install`.

2. **MCP Server Configuration:**
   The install script will prompt for MCP secrets interactively. If the user needs help:
   - **GitHub**: They need a Personal Access Token from https://github.com/settings/tokens
   - **Atlassian**: They need their Atlassian email and an API token from https://id.atlassian.com/manage-profile/security/api-tokens
   - **Google Drive**: They need an OAuth credentials JSON from Google Cloud Console
   - **BigQuery**: No credentials needed (uses Google's hosted MCP)

3. **After install:** Tell the user to restart Claude Code (`claude` in terminal) so the new config takes effect.

## What Gets Installed

| Component | Count | Location |
|-----------|-------|----------|
| Slash commands | 17 | `~/.claude/commands/` |
| Skills | 28 | `~/.claude/skills/` |
| Agents | 8 | `~/.claude/agents/` |
| Hooks | 7 | `~/.claude/hooks/` |
| Scheduled tasks | 1 | `~/.claude/scheduled/` |
| Settings | 1 | `~/.claude/settings.json` |
| MCP servers | 4 (GitHub, Atlassian, Google Drive, BigQuery) | Stdio: `~/.claude/.mcp.json`, HTTP: `~/.claude.json` via `claude mcp add` |

## Key Skills to Mention

After setup, tell the user about these commonly used commands:
- `/go` or `/go-devloop` — Implement a Jira ticket end-to-end with quality loops
- `/plan` — Plan before coding
- `/code-review` — Review uncommitted changes
- `/tdd` — Test-driven development
- `/build-fix` — Fix build/TypeScript errors
- `/claudia` — Debug investigation for hard bugs
- `/kt` — Generate knowledge-transfer documentation
- `/job-scanner-setup` — Set up a personalized daily job-market scanner

## Running trycycle (IMPORTANT)

`trycycle` (invoked directly, via `/tc`, or by `/go` → `go-devloop`) dispatches
subagents for planning, implementation, and review. It supports two transports:

1. **Native** — the host agent's built-in subagent facility
2. **Fallback** — `orchestrator/subagent_runner.py`, which spawns fresh
   `claude -p ...` subprocesses

**In Claude Code, always use native transport.** Dispatch every trycycle
subagent via the `Task` tool (`subagent_type: general-purpose`), and resume
persistent subagents (the implementation agent across review-fix rounds) via
the `Task` tool's `resume` parameter using the returned agent ID.

**Never call `~/.claude/skills/trycycle/orchestrator/subagent_runner.py`
from inside a Claude Code session.** The Claude Code CLI has a hard guard
against nested sessions:

> Error: Claude Code cannot be launched inside another Claude Code session.
> Nested sessions share runtime resources and will crash all active sessions.
> To bypass this check, unset the CLAUDECODE environment variable.

When the runner hits this, trycycle surfaces it as
*"Trycycle cannot nest Claude Code sessions in this environment"* and the
run stalls. Trycycle's own SKILL.md (`## Subagent transport`) explicitly
says: *"If your environment can natively dispatch, wait on, and resume
subagents, use that native facility. In native mode, do not use the
fallback runner."* Claude Code's `Task` tool qualifies — use it.

If native dispatch is unavailable in the current session, **stop and tell
the user** instead of falling back to the runner. The repo installs
trycycle as a submodule and users run it from inside Claude Code, so native
is the only working path.

The other trycycle helpers are pure Python and fine to invoke directly:
`orchestrator/prompt_builder/build.py`,
`orchestrator/user-request-transcript/*.py`, and `check-update.py`.
Only `subagent_runner.py` is forbidden.

### One-shot directive users can paste when invoking trycycle

```
Use trycycle to <task>.

Transport: native only. Dispatch every trycycle subagent via the Claude
Code Task tool (subagent_type: general-purpose), and resume persistent
ones via the Task tool's `resume` parameter with the returned agent ID.
Do NOT invoke <skill-dir>/orchestrator/subagent_runner.py under any
circumstances — it will fail with "Claude Code cannot be launched
inside another Claude Code session". If native dispatch is not possible,
stop and tell me instead of falling back.
```

## Updating

To update to the latest config:
```bash
cd claude-code-starter
git pull --recurse-submodules
./install.sh
```

## Local Agents MCP (`local-agents`)

If the `local-agents` MCP server is available (registered in `~/.claude.json`), use its tools proactively instead of burning the main context window on file exploration:

| Situation | Tool to reach for |
|-----------|-----------------|
| "How does X work in this codebase?" | `explore_lite(task, repo)` — fast, no memory needed |
| Deep investigation spanning many files | `explore(task, repo)` — uses shared memory, resumable |
| Recurring Q&A about a repo | `codebase_qa(question, repo)` — cited answers, auto-saved to memory |
| Any git/GitHub task in plain English | `git_yoda(task, repo)` — dry-run by default |
| Writing a PR description | `pr_desc(repo)` — generates What/Why/How to Test/Risks |
| Saving a decision for future sessions | `memory_remember(text, namespace)` |
| Recalling prior work | `memory_recall(query, namespace)` |
| Ending a long session | `save_handover(note, repo, session)` |
| Starting a new session on prior work | `explore(task, repo, resume=true)` |

**All tools are optional** — if the server is not running or memory is unavailable, fall back to normal file tools. Never fail a task just because `local-agents` is unreachable.

## Important

- NEVER commit secrets (API tokens, credentials) to this repo
- The `mcp-servers.json.template` has placeholders — each user fills in their own secrets during install
- Backups of previous config are saved to `~/.claude/backups/`
