You are running a session handover. Your job is to distill this session down to the 5% worth carrying forward and produce a short handover note the next session can read in under 30 seconds. Filter aggressively — most execution is forgettable.

## Step 1: Survey the session

Run these in parallel:
- `git log --oneline --since="8 hours ago"` (commits made this session)
- `git status` (uncommitted changes)
- `git diff --stat HEAD` (what's staged/unstaged)

Also check the active task list for anything in-progress or completed this session.

## Step 2: Identify what's load-bearing

From the session evidence, extract only what the next session needs:
- **Decisions made** — architectural choices, tradeoffs accepted, things ruled out
- **Constraints discovered** — limits, gotchas, things that turned out to be harder than expected
- **Half-finished work** — what state is it in, what's the next concrete step
- **Broken assumptions** — anything that turned out to be wrong about the codebase or requirements

Ignore: routine file edits, test runs that passed, commands that worked as expected, anything that left no lasting consequence.

## Step 3: Update persistent memory (selective)

Find the auto memory file for this project. The path follows this pattern:
`~/.claude/projects/<encoded-cwd>/memory/MEMORY.md`

Where `<encoded-cwd>` is the current working directory with `/` replaced by `-` and no leading `-`.

Example: if cwd is `/Users/alice/myproject`, the path is `~/.claude/projects/-Users-alice-myproject/memory/MEMORY.md`.

Read the current MEMORY.md. Then update **only entries that future-you will need** based on Step 2:
- Add new constraints, decisions, or patterns discovered this session
- Update or correct any entries that turned out to be wrong
- Do NOT log daily activity, task completions, or "we worked on X today"
- Keep MEMORY.md under 200 lines — compress or remove stale entries if needed

## Step 4: Handle uncommitted changes

If there are uncommitted changes worth preserving:
- Describe what they are and ask the user: "There are uncommitted changes to [files]. Want me to commit them before wrapping up?"
- Wait for a yes/no before doing anything
- If yes, propose a commit message and confirm before committing

If there are no meaningful uncommitted changes, skip this step silently.

## Step 5: Print the handover note

Output a structured note with exactly these four sections. Keep each section tight — 2–5 bullet points max. If a section is empty, write "Nothing significant."

---

## Handover — [date]

### Shipped this session
[Commits made, features completed, PRs merged, deploys. List by commit hash + message if available.]

### In flight
[Work that was started but not finished. Include: what it is, what state it's in, what the next concrete action is.]

### Watch-outs
[Gotchas, surprising state, broken assumptions, footguns hit. Things that would bite the next session if they didn't know.]

### Open questions
[Unresolved decisions, things to look up, blockers that need external input.]

---

Keep the total note short enough to read in under 30 seconds. When in doubt, cut it.
