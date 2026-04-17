Create a named checkpoint of the current project state for progress tracking and rollback.

## Operations

- `create <name>` — Verify clean state, create git stash or commit, log to `.claude/checkpoints.log`
- `verify <name>` — Compare current state to checkpoint (files changed, test pass rate, coverage)
- `list` — Show all checkpoints with name, timestamp, git SHA, status
- `clear` — Remove old checkpoints, keep the most recent 5

## Usage

```
/checkpoint create feature-start
/checkpoint verify feature-start
/checkpoint list
/checkpoint clear
```

## Typical Workflow

1. `/checkpoint create feature-start` — before beginning work
2. `/checkpoint create core-impl` — after core implementation
3. `/checkpoint verify feature-start` — compare progress
4. `/checkpoint create post-refactor` — after cleanup
5. `/checkpoint verify core-impl` — final verification before PR

Arguments: $ARGUMENTS
