# Task: <human-readable title>

<!--
Copy this file to `<task-id>.task.md` and fill in every field.
`<task-id>` must be kebab-case (letters, digits, hyphens) — it becomes the storage key.
Keep exactly one of `cron` or `fireAt`. Delete the other line.
-->

- **taskId:** `my-task-id`
- **description:** One-line summary of what this task does.
- **schedule (cron):** `0 9 * * *`   <!-- local time; OR delete and use fireAt below -->
- **schedule (fireAt):** `2026-07-01T15:00:00-07:00`   <!-- one-time; OR delete and use cron above -->

## Prompt (runs on each fire — must be fully self-contained)

```
Write the complete instructions Claude should execute every time this task fires.

Be explicit and standalone — the run has NO memory of any chat:
- Which connectors/MCP servers to use (e.g. GitHub, Atlassian, Slack, google-drive).
- The exact output: where it goes (a Slack channel? a file? just the chat?) and its format.
- Any preferences, filters, accounts, repos, or thresholds.
```
