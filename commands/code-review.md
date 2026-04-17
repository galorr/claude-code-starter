Invoke the code-reviewer agent to review all uncommitted changes.

Process:
1. Run `git diff --name-only HEAD` to identify changed files
2. Review each file across all severity tiers
3. Report findings with file:line references and fix suggestions
4. Output a verdict: APPROVE / WARNING / BLOCK

Severity tiers checked:
- **CRITICAL**: Security vulnerabilities (credentials, SQLi, XSS, auth bypass)
- **HIGH**: Code quality (function size, nesting, missing error handling), framework patterns
- **MEDIUM**: Performance issues
- **LOW**: Best practices, documentation

**Never approve code with CRITICAL or HIGH security issues.**

Scope: $ARGUMENTS (default: all uncommitted changes)
