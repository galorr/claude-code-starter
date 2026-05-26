# GitHub Playbook

How Claudia uses GitHub evidence. Read this when the investigation involves "what changed?", suspect commits, or understanding the actual implementation.

## The "what changed" query

For any regression — something that used to work and now doesn't — the first GitHub question is: **what merged between the last known good state and the first bad state?**

1. Establish the two points. "Worked in v2.4.1, broken in v2.5.0." Or "worked yesterday at 14:00 UTC, broken today at 09:00 UTC."
2. Pull the commit/PR list between them, filtered to the services or paths implicated by APM evidence.
3. Read the suspect PRs — not just the titles. Look at the diff.

Don't just read the PR description. PR descriptions often describe the intent, not the actual change. Read the diff.

## Reading code to verify a hypothesis

Once you have a suspect commit or a suspect code path:

- Pull the actual file at the relevant version. Don't reason from the commit title.
- Trace the execution path from the entry point to the failure. If you can't follow it end-to-end, your hypothesis isn't grounded yet.
- Pay attention to error handling. Bugs often live in the `catch` branch that no one tests.
- Pay attention to assumptions — null checks that were omitted, types that were trusted, concurrent access that wasn't guarded.

## Useful search patterns

- **Code search for the exact error message.** If the error string appears verbatim in the codebase, you've found the throw site.
- **Recent PRs touching the file/module.** Even if not in the release window, recent churn on a file is a hotspot.
- **Issues mentioning similar symptoms.** Someone may have reported this before the current user.
- **Blame on the failing line.** Who touched this last, and in what PR? Read that PR's discussion.

## When to suggest a bisect

If you have a clear "good" and "bad" version and the commit range is large (>20 commits) and unreadable by inspection, recommend `git bisect`. Don't run it yourself — give the user the bisect commands and the test to run at each step. Bisect only works if there's a deterministic reproduction.

## Cross-repo investigations

If the service pulls in internal libraries, the bug may be in a dependency, not in the service itself. Check the version bumps in the suspect PRs — a library version bump is often the real culprit, hidden under a "dependency update" PR title.

## What to cite in the writeup

For each GitHub finding referenced in your report, capture:

- The **commit SHA** (full, not short) or **PR number**
- The **file and line number** if pointing at a specific location
- A **1-2 line quote** of the relevant code (not the whole function — just the piece that matters)
- Link to the PR discussion if there's useful context in the review comments
