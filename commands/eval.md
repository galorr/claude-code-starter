Manage eval-driven development workflows for a feature.

## Operations

- `define <feature>` — Create eval definition at `.claude/evals/<feature>.md` with capability evals, regression evals, and success criteria
- `check <feature>` — Run evals, verify each criterion, log results
- `report <feature>` — Generate comprehensive report with pass@1, pass@3 rates, and SHIP/NEEDS WORK/BLOCKED recommendation
- `list` — Show all evals with status and completion percentage
- `clean` — Remove old eval logs, keep last 10 runs

## Eval Definition Format

```markdown
# Evals: [Feature Name]

## Capability Evals
- [ ] [What the feature should be able to do]

## Regression Evals
- [ ] [What must not break]

## Success Criteria
- pass@1: X%
- pass@3: X%
```

## Usage

```
/eval define auth-flow
/eval check auth-flow
/eval report auth-flow
```

Release-critical paths should target pass^3 stability before merge.

Arguments: $ARGUMENTS
