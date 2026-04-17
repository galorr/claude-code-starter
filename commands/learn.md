Analyze the current session and extract any patterns worth saving as reusable skills.

## What to Extract

Look for:

1. **Error Resolution Patterns** — What error occurred, root cause, what fixed it, is it reusable?
2. **Debugging Techniques** — Non-obvious debugging steps, tool combinations that worked
3. **Workarounds** — Library quirks, API limitations, version-specific fixes
4. **Project-Specific Patterns** — Codebase conventions discovered, architecture decisions, integration patterns

## Process

1. Review the session for extractable patterns
2. Identify the most valuable/reusable insight
3. Draft the skill file content
4. Ask the user to confirm before saving
5. Save to `~/.claude/skills/learned/[pattern-name].md`

## Output Format

```markdown
# [Descriptive Pattern Name]

**Extracted:** [Date]
**Context:** [Brief description of when this applies]

## Problem
[What problem this solves]

## Solution
[The pattern/technique/workaround]

## Example
[Code example if applicable]

## When to Use
[Trigger conditions]
```

## Rules

- Don't extract trivial fixes (typos, simple syntax errors)
- Don't extract one-time issues (specific API outages)
- Focus on patterns that will save time in future sessions
- Keep skills focused — one pattern per skill file

Context: $ARGUMENTS
