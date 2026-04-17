Invoke the build-error-resolver agent to fix build and TypeScript errors with minimal changes.

Process:
1. Detect build system and run the build
2. Collect and categorize all errors
3. Fix one error at a time with the smallest possible diff
4. Re-run build after each fix to verify no regressions
5. Report all fixed errors and any remaining blockers

Rules:
- **Minimal diffs only** — no refactoring, no architecture changes
- **Stop and ask** if a fix introduces more errors than it resolves
- **Stop and ask** if the same error persists after 3 attempts

Stop condition: build exits with code 0.

Scope: $ARGUMENTS (default: current project)
