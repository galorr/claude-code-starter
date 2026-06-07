---
name: handover
description: End-of-session handover — surveys what happened, updates auto memory with only future-relevant context, and prints a structured note (shipped / in-flight / watch-outs / open questions).
when_to_use: "Trigger on /handover, 'wrapping up', 'done for the day', or when the user is ending a session."
argument-hint: "[optional: any open questions or context to include in the handover]"
effort: low
---

# Handover

You are generating an end-of-session handover. Be ruthlessly selective — most of a session is forgettable execution. Your job is to extract the 5% worth carrying forward so the next session can start without losing context.

---

## Step 1 — Survey the session

Run these in parallel:

```bash
# What was committed this session (approximate: last 12 hours, no merges)
git log --since="12 hours ago" --oneline --no-merges 2>/dev/null || echo "(not a git repo)"

# Current dirty state
git status --short 2>/dev/null || echo "(not a git repo)"

# Any stashed work
git stash list 2>/dev/null || echo "(none)"
```

Also check `TaskList` for any tasks marked done vs. still in-flight.

Then scan the conversation context for: what was the user trying to accomplish? What actually happened?

---

## Step 2 — Filter aggressively

From the survey, identify only what's **load-bearing** for the next session.

**Carry forward (worth preserving):**
- Decisions made that constrain future work
- Constraints or gotchas discovered during this session
- Half-finished work with enough context to resume cold
- Broken assumptions that changed the approach
- Open questions the user needs to resolve

**Discard (do not include):**
- Routine execution (commands run, files read, tests passed)
- Details that are obvious from reading the code
- Anything recoverable by just looking at the files

If a section has nothing real to say, write "None." — don't pad it.

---

## Step 3 — Update auto memory (only if warranted)

Compute the project memory path and read the current MEMORY.md:

```bash
MEMORY_FILE="$HOME/.claude/projects/$(pwd | sed 's|^/||; s|/|-|g')/memory/MEMORY.md"
cat "$MEMORY_FILE" 2>/dev/null && echo "---PATH: $MEMORY_FILE" || echo "(no memory file at $MEMORY_FILE)"
```

Update MEMORY.md **only** if this session produced information that future sessions need but can't easily recover from the codebase:
- Architectural decisions made
- Discovered constraints or footguns that aren't obvious from the code
- Non-obvious project state (broken tool, pending dependency, environment quirk)

**Do NOT write:**
- A log of today's activity ("today we worked on X")
- Things already obvious from the codebase or README
- Speculative info not yet confirmed
- Duplicate entries that already exist in memory

If no memory update is warranted, skip this step silently. When in doubt, skip — memory files that grow with daily activity become useless noise.

---

## Step 4 — Handle uncommitted changes

If `git status` shows uncommitted changes:

1. Determine whether they represent real progress worth committing, or just scratch/WIP that should stay uncommitted.
2. If worth committing, **ask the user before doing anything:**
   > "There are uncommitted changes to [list key files]. Worth committing? I'd use: `[proposed commit message]`"
3. Only commit if the user explicitly confirms.
4. If the changes are clearly throwaway (debug prints, temp files, experiments), note them in Watch-outs instead.

Never commit without explicit user confirmation.

---

## Step 5 — Print the handover note

Output this structure. Keep the entire note short enough to read in under 30 seconds.

```
---

## Handover — [today's date]

### Shipped
[One line per commit made this session: "<hash> — <message>". If nothing shipped: "Nothing committed."]

### In flight
[Work started but not finished. Include enough context that a cold reader could pick it up: what's the goal, where it's at, what the next step is. If nothing: "Nothing in flight."]

### Watch-outs
[Gotchas, surprising state, broken assumptions discovered this session. Things the next session should know before diving in. If none: "None."]

### Open questions
[Things the user needs to decide, investigate, or follow up on. Include any arguments passed to /handover. If none: "None."]

---
```

**Quality bar:** If a section would only say something the user already knows, cut it. Each bullet should provide value a cold reader wouldn't have from the code alone.
