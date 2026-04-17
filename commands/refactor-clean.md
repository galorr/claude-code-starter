Invoke the refactor-cleaner agent to safely identify and remove dead code.

Process:
1. Run detection tools: `npx knip`, `npx depcheck`, `npx ts-prune`
2. Categorize findings: SAFE / CAREFUL / RISKY
3. Start with SAFE items only — verify each with grep before removing
4. Run full test suite after each batch
5. Commit each batch with a descriptive message
6. Consolidate near-duplicate code after dead code is removed

Rules:
- **Never delete without running tests first**
- **One batch at a time** — atomic changes make rollback easy
- **Skip if uncertain** — better to keep dead code than break production
- **Do not refactor while cleaning** — separate concerns

Scope: $ARGUMENTS (default: current project)
