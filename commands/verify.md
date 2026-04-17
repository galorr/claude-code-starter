Run comprehensive verification on the current codebase state and produce a pass/fail report.

## Verification Order (run in sequence, stop on FAIL)

1. **Build Check** — Run the project build command; stop and report if it fails
2. **Type Check** — Run TypeScript checker; report all errors with file:line
3. **Lint Check** — Run linter; report warnings and errors
4. **Test Suite** — Run all tests; report pass/fail count and coverage %
5. **Console.log Audit** — Search for console.log in source files; report locations
6. **Git Status** — Show uncommitted changes and files modified since last commit

## Output Format

```
VERIFICATION: [PASS/FAIL]

Build:    [OK/FAIL]
Types:    [OK/X errors]
Lint:     [OK/X issues]
Tests:    [X/Y passed, Z% coverage]
Logs:     [OK/X console.logs found]
Git:      [X files uncommitted]

Ready for PR: [YES/NO]
```

If any critical issues found, list them with fix suggestions.

## Arguments

$ARGUMENTS can be:
- `quick` — Only build + types
- `full` — All checks (default)
- `pre-commit` — Checks relevant for commits
- `pre-pr` — Full checks plus security scan
