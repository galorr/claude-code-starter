# Scheduled Tasks — drop-in kit

This folder holds **portable scheduled tasks**. Each task is two files:

| File | Purpose |
|------|---------|
| `<task>.prompt.md` | The "drop it in Claude" message. Paste its contents (or say *"do what `scheduled/<task>.prompt.md` says"*) and Claude registers the task. |
| `<task>.task.md` | The task definition: schedule + the full self-contained prompt that runs on each fire. |

## How to add a task to Claude

Open Claude Code in this repo and paste:

> Read `scheduled/daily-standup.task.md` and create the scheduled task it describes using the `scheduled-tasks` MCP (`create_scheduled_task`). Use the `taskId`, `schedule`, and `prompt` exactly as written.

That's it — Claude reads the definition and calls `create_scheduled_task`. The approval
dialog Claude shows is the confirmation step.

## How tasks run

- Scheduled tasks run **while the Claude app is open**. If the app is closed when a task is
  due, it runs on next launch.
- Each run starts **fresh with no memory** of any prior conversation — so the `prompt` in
  the `.task.md` must be fully self-contained (which connectors to use, output format, any
  preferences).

## Schedule formats

Pick **one** per task:

- **Recurring** — a 5-field cron expression in your **local** timezone:
  `minute hour day-of-month month day-of-week`
  - `0 9 * * *` — every day 09:00
  - `0 9 * * 1-5` — weekdays 09:00
  - `30 8 * * 1` — Mondays 08:30
  - `0 0 1 * *` — first of each month, midnight
- **One-time** — an ISO 8601 timestamp with offset: `2026-07-01T15:00:00-07:00`
  (fires once, then auto-disables).

## Files here

- `TEMPLATE.task.md` / `TEMPLATE.prompt.md` — copy these to start a new task.
- `daily-standup.task.md` / `daily-standup.prompt.md` — a filled-in example.

## Exporting your existing tasks back into this folder

If you later have live scheduled tasks and want to snapshot them here, paste:

> List my scheduled tasks with the `scheduled-tasks` MCP. For each one, write a
> `scheduled/<taskId>.task.md` (schedule + full prompt) and a matching
> `scheduled/<taskId>.prompt.md` drop-in, following the format in `scheduled/README.md`.
