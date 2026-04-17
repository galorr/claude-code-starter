Audit the current repository's agent harness setup and return a prioritized scorecard.

## Usage

`/harness-audit [scope] [--format text|json]`

- `scope`: `repo` (default), `hooks`, `skills`, `commands`, `agents`
- `--format`: `text` (default) or `json` for automation

## What to Score (0–10 each)

1. **Tool Coverage** — Are the right agents/skills available for common tasks?
2. **Context Efficiency** — Are hooks and prompts lean and non-redundant?
3. **Quality Gates** — Are lint, type, test hooks in place?
4. **Memory Persistence** — Is session state saved across compactions/restarts?
5. **Eval Coverage** — Are key features covered by evals?
6. **Security Guardrails** — Are security hooks and rules in place?
7. **Cost Efficiency** — Is model routing appropriate (haiku for simple, opus for complex)?

## Output

```
Harness Audit (repo): XX/70

- Tool Coverage:      X/10
- Quality Gates:      X/10
- Memory Persistence: X/10
- ...

Top 3 Actions:
1) [specific action with file path]
2) [specific action with file path]
3) [specific action with file path]
```

## Checklist

- Inspect `~/.claude/hooks/` and `settings.json` hooks config
- Inspect `~/.claude/skills/`, `~/.claude/commands/`, `~/.claude/agents/`
- Flag broken or stale file references
- Flag missing coverage for common development tasks

Arguments: $ARGUMENTS
