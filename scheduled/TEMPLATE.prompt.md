<!--
Drop-in prompt. Replace `<task-id>` with your task's id, then paste the block
below (the quoted lines) into Claude Code running in this repo.
-->

> Read `scheduled/<task-id>.task.md` and create the scheduled task it describes
> using the `scheduled-tasks` MCP tool `create_scheduled_task`.
>
> - Use the `taskId` and `description` from the file.
> - If the file has a cron schedule, pass it as `cronExpression`; if it has a
>   `fireAt` timestamp instead, pass it as `fireAt`. Never pass both.
> - Use the fenced **Prompt** block from the file verbatim as the `prompt`.
>
> Then confirm the task was created and tell me its next run time.
