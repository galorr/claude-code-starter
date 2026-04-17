Run the quality pipeline on demand for a file or project scope.

Mirrors the automated hook behavior but is operator-invoked for manual runs.

## Usage

`/quality-gate [path|.] [--fix] [--strict]`

- Default target: current directory (`.`)
- `--fix` — Allow auto-format/fix where configured (prettier, eslint --fix)
- `--strict` — Fail on warnings as well as errors

## Pipeline

1. Detect language and tooling for the target path
2. Run formatter check (prettier)
3. Run lint check (eslint, with `--max-warnings=0` if `--strict`)
4. Run type check (tsc --noEmit) if TypeScript project
5. Produce concise remediation list for any failures

## Output

```
Quality Gate: [PASS/FAIL]

Format:  [OK/X issues]
Lint:    [OK/X errors, Y warnings]
Types:   [OK/X errors]

[list of issues with file:line and fix suggestions]
```

Arguments: $ARGUMENTS
