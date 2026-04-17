Start a managed autonomous loop pattern with safety defaults.

## Usage

`/loop-start [pattern] [--mode safe|fast]`

**Patterns:**
- `sequential` — Execute tasks one by one in dependency order
- `continuous-pr` — Loop: implement → test → PR → next task
- `rfc-dag` — RFC-driven directed acyclic graph execution
- `infinite` — Continuous improvement loop (requires explicit stop condition)

**Modes:**
- `safe` (default) — Strict quality gates and checkpoints at each iteration
- `fast` — Reduced gates for speed, use only for low-risk tasks

## Flow

1. Confirm repository state and branch strategy
2. Select loop pattern and model tier strategy
3. Verify tests pass before first iteration
4. Create loop plan and write runbook to `.claude/plans/`
5. Execute with checkpoints between iterations

## Required Safety Checks

- Tests must pass before the first loop iteration starts
- Every loop must have an explicit stop condition defined
- `safe` mode is default — don't use `fast` for anything touching production

## Stop Condition

Always define before starting:
- "Stop after N iterations"
- "Stop when all items in list X are complete"
- "Stop when test coverage reaches Y%"

Arguments: $ARGUMENTS
