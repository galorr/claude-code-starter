# Task: Daily standup summary

- **taskId:** `daily-standup`
- **description:** Post a standup summary of my recent activity every weekday morning.
- **schedule (cron):** `0 9 * * 1-5`

## Prompt (runs on each fire — must be fully self-contained)

```
Generate my daily standup update for today.

Sources:
- GitHub: my commits, opened/merged PRs, and review requests from the last 24 hours.
- Jira (Atlassian MCP): issues assigned to me that changed status in the last 24 hours,
  plus anything currently in progress.

Format the update as three short sections:
- Yesterday: what I completed (bullet list).
- Today: what I plan to work on, inferred from in-progress issues (bullet list).
- Blockers: anything stalled, waiting on review, or flagged blocked — or "None".

Keep it tight (one line per bullet). Output the formatted update directly in the chat.
```
