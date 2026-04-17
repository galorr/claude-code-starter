---
name: go-devloop
description: Unified development orchestrator that combines Jira/Figma integration (from codepilot) with iterative quality loops (from trycycle). Auto-detects UI vs backend tickets and routes accordingly. Use when the user provides a Jira ticket link and wants high-quality autonomous development. Trigger on "go-devloop", "go", "implement this ticket with quality", or when the user wants the best of both codepilot and trycycle.
context: fork
agent: general-purpose
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Agent, Skill, mcp__atlassian__getJiraIssue, mcp__atlassian__editJiraIssue, mcp__atlassian__addCommentToJiraIssue, mcp__atlassian__getTransitionsForJiraIssue, mcp__atlassian__transitionJiraIssue
---

# DevLoop — Unified Development Orchestrator

Combines Codepilot's Jira/Figma/PR pipeline with Trycycle's iterative quality loops.
Auto-detects whether a ticket is UI or backend and routes to the appropriate workflow.

## Required Inputs
- Jira ticket URL
- (Optional) User availability: `available` | `unavailable`

---

## Phase 0: Repository Initialization Check

Before starting any work, check if a `CLAUDE.md` file exists at the repository root:

```bash
test -f CLAUDE.md && echo "exists" || echo "missing"
```

- **If `CLAUDE.md` is missing** → run `/init` to initialize the repository context before proceeding. This ensures the AI has proper project context for all subsequent phases.
- **If `CLAUDE.md` exists** → skip this phase and proceed to Phase 1.

---

## Phase 1: Retrieve & Parse Ticket

Fetch ticket from Jira MCP using `mcp__atlassian__getJiraIssue`.

```
Fields to extract:
- ticket.title
- ticket.description
- ticket.acceptanceCriteria
- ticket.figmaLinks[]
- ticket.apiContracts[]
- ticket.relatedComponents[]
- ticket.relatedServices[]
- ticket.databaseChanges[]
- ticket.labels[]
- ticket.type (Story, Bug, Task, etc.)
```

If critical fields are missing and user is unavailable → send clarification question, poll for response every 30 seconds.

Transition ticket to **In Progress** using `mcp__atlassian__getTransitionsForJiraIssue` + `mcp__atlassian__transitionJiraIssue` (look for a transition named "In Progress" or "In Progress - Direct").

---

## Phase 1.5: Branch Setup

Before proceeding, check the current git branch and ask the user how they want to handle branching:

1. Run `git branch --show-current` to get the current branch name.
2. Ask the user:
   > "You're currently on branch `<current-branch>`. How would you like to proceed?"
   >
   > - **Use current branch** (`<current-branch>`) — continue working here
   > - **Create a new branch** — I'll create `fix/<TICKET-KEY>-<short-description>` from the latest default branch

3. If the user chooses to create a new branch:
   - **Always** create the branch from the up-to-date default branch (never from the current branch). First fetch from remote, refresh `origin/HEAD` so it reflects the real default branch, then branch off of it:
     ```bash
     git fetch origin
     git remote set-head origin -a
     DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')
     git checkout -b <branch-name> "origin/$DEFAULT_BRANCH"
     ```
   - Derive the branch name from the ticket key and title: `fix/<TICKET-KEY>-<kebab-case-short-title>` (for bugs) or `feat/<TICKET-KEY>-<kebab-case-short-title>` (for features/stories).
   - Present the suggested name and let the user override it.
4. If the user chooses to stay on the current branch → proceed without changes.

---

## Phase 2: Classify Ticket — UI or Backend

Analyze the ticket content to determine the type. Use these signals:

### UI Ticket Signals
- Has Figma links in description or attachments
- Labels contain: `frontend`, `ui`, `angular`, `component`, `design`, `css`, `ux`
- Description mentions: components, UI, layout, styles, design, responsive, view, page, modal, dialog, form (in UI context)
- Related components are Angular components/modules
- Ticket type/summary suggests visual work

### Backend Ticket Signals
- Has API contracts, Swagger, or OpenAPI links
- Labels contain: `backend`, `api`, `nestjs`, `service`, `database`, `migration`, `endpoint`
- Description mentions: API, endpoint, controller, service, database, migration, schema, DTO, guard, interceptor, queue, event
- Related services are NestJS modules/services
- Ticket mentions data models, queries, or integrations

### Decision Logic
1. If clear signals for one type → auto-classify and inform user
2. If mixed signals (e.g., full-stack ticket) → ask user: "This ticket has both UI and backend elements. Which should I focus on — **UI** or **Backend**?"
3. If unclear → ask user to clarify

Store result as `ticketType: 'ui' | 'backend'`.

---

## Phase 3: Domain-Specific Context Gathering

### If UI ticket:

**3a. Pull Figma Designs**
For each URL in `ticket.figmaLinks[]`:
- Fetch full-page screenshots
- Capture developer frame links
- Store as `figmaContext`

**3a.5. Search Golden Repos & Internal Docs**
- Search the frontend golden repo for Angular patterns matching the ticket's UI concepts
  (See: `skills/_shared/references/sourcegraph-search.md`)
- Search shared libraries for shared UI utilities or components
- Search Confluence for relevant design system docs or conventions
  (See: `skills/_shared/references/documentation-search.md`)
- Log all patterns and docs found for use in architecture planning

**3b. Architecture Planning (Frontend)**
Produce component architecture:
```typescript
{
  componentPath: string;
  components: Array<{
    name: string;
    responsibility: string;
    inputs?: string[];
    outputs?: string[];
  }>;
  state: {
    signals: string[];
    services: string[];
    communication: string[];
  };
  events: string[];
  sharedModules: string[];
}
```

### If Backend ticket:

**3a. Analyze Existing Codebase & API Contracts**
- Scan NestJS project structure (apps/, libs/, module boundaries)
- Identify existing modules, services, controllers related to the ticket
- Review existing API contracts (Swagger decorators, DTOs, OpenAPI specs)
- Check for existing database entities/schemas
- Identify shared libraries and common patterns
- **Search golden repos** for established patterns matching the ticket's technical concepts
  (See: `skills/_shared/references/sourcegraph-search.md`)
  - Search the backend golden repo for NestJS patterns (guards, interceptors, services, DTOs)
  - Search shared libraries for reusable shared utilities
  - Log patterns found for use in architecture planning
- **Search internal documentation** for relevant ADRs and guidelines
  (See: `skills/_shared/references/documentation-search.md`)
  - Search Confluence for architecture decisions in this feature area
  - Log documentation references

**3b. Architecture Planning (Backend)**
Produce API architecture:
```typescript
{
  modulePath: string;
  module: { name, imports, controllers, providers, exports };
  controllers: Array<{ name, basePath, endpoints[] }>;
  services: Array<{ name, responsibility, dependencies[], methods[] }>;
  dtos: Array<{ name, purpose, validationRules[] }>;
  entities: Array<{ name, tableName, fields[], relations[] }>;
  guards: string[];
  interceptors: string[];
  migrations: string[];
}
```

Write the architecture plan to `architecture.md`.

**If a major architectural decision is needed** → present 2-4 options to user before proceeding.

---

## Phase 4: Delegate to Trycycle for Iterative Quality Loop

Now hand off to `/trycycle` for the iterative planning, implementation, and review cycle.

Invoke `/trycycle` with the following context prepended to the user's original request:

```
CONTEXT FROM DEVLOOP ORCHESTRATOR:
- Jira Ticket: [TICKET-KEY] - [ticket.title]
- Ticket Type: [ui|backend]
- Description: [ticket.description]
- Acceptance Criteria: [ticket.acceptanceCriteria]
- Architecture Plan: See architecture.md at [path]
[If UI]: - Figma Designs: [figmaContext summary]
[If Backend]: - API Contracts: [apiContracts summary]
[If Backend]: - Database Changes: [databaseChanges summary]

TASK: Implement the feature described above following the architecture plan.
The architecture plan is already written — use it as the implementation contract.
```

Trycycle will handle:
- Testing strategy (Phase 3 of trycycle)
- Worktree creation (Phase 4)
- Multi-round planning refinement (Phases 6-7, up to 5 rounds)
- Test plan creation (Phase 8)
- Implementation (Phase 9)
- Post-implementation review loop (Phase 10, up to 8 rounds)
- Finish & integration options (Phase 11)

**Important:** Let trycycle run its full cycle. Do not interfere with its internal loops.

---

## Phase 5: Post-Trycycle Validation

After trycycle completes and the user has approved the implementation:

### If UI ticket:
Invoke `/output-validator` to validate against Figma designs:
```typescript
{
  ticketContext,
  figmaContext,
  liveUrl: "http://localhost:PORT/feature-route"
}
```

Validator checks:
- Visual match against Figma
- All `acceptanceCriteria` satisfied
- Accessibility basics

If rejected → report issues to user and ask how to proceed.

### If Backend ticket:
Run final validation:
```bash
npx nx build <project-name>
npx nx test <project-name>
```

Verify:
- All acceptance criteria satisfied
- Swagger decorators present on all endpoints
- DTOs have proper validation decorators
- No circular dependencies
- Error handling follows project conventions

---

## Phase 6: Auto Commit, Push & Open PR

**Do NOT stop or ask for approval here.** After the implementation has passed trycycle's quality loop and Phase 5 validation, automatically commit, push, and open a PR.

1. Inspect the commit convention from recent `git log --oneline -20` and follow it.
2. Stage only the files changed by this ticket (never `git add -A`):
```bash
git add <specific files>
git commit -m "feat: [TICKET-KEY] <feature description>"
git push --set-upstream origin <branch-name>
```

3. Open a PR against the appropriate base branch and **capture the URL**:
```bash
PR_URL=$(gh pr create --title "feat: [TICKET-KEY] ..." --body "..." --base staging)
```

4. **Display the PR URL in bold orange so the user can clearly see it.** Print it via bash using ANSI escape codes (orange = 38;5;208, bold = 1):
```bash
printf '\n\033[1;38;5;208m PR: %s\033[0m\n\n' "$PR_URL"
```

Also emit the URL in the assistant text output as **`PR: <url>`** in bold markdown, so it is visible both in the terminal stream and in the conversation.

5. After the PR is created, transition the Jira ticket to **Code Review** using `mcp__atlassian__getTransitionsForJiraIssue` + `mcp__atlassian__transitionJiraIssue` (look for a transition named "Code Review", "In Review", or "Review").

**Never** skip this phase. **Never** prompt the user before committing, pushing, or opening the PR — this is the whole point of `/go`.

---

## Phase 6.5: Update Documentation

After the main commit and push, update project documentation in a **separate commit**:

1. **Update README** — invoke `/update-docs` to sync the README with any new features, endpoints, components, or setup changes introduced by this ticket.
2. **Update CLAUDE.md** — reflect any new conventions, key files, patterns, or architectural decisions discovered during implementation.

Commit and push documentation updates separately:
```bash
git add README.md CLAUDE.md
git commit -m "docs: [TICKET-KEY] update README and CLAUDE.md"
git push
```

This keeps feature code and documentation changes in distinct commits for cleaner git history.

---

## Phase 7: Zip-Agent Automated Review Scan

After the PR is created, **wait 5 minutes** for automated reviewers (zip-agent) to post comments:

```bash
sleep 300
```

Then scan all PR comments for zip-agent feedback:
```bash
gh api repos/<owner>/<repo>/pulls/<pr_number>/comments --hostname <github_hostname>
```

Filter for comments from `zip-agent` (or similar automated reviewer bots).

### Classify each comment:

| Category | Action |
|----------|--------|
| **Non-logic** (style, formatting, naming, imports, lint, typos, documentation) | Fix automatically, commit and push without user approval |
| **Logic** (architecture, algorithm, business logic, security, data flow) | Present to user for review — do NOT fix without explicit approval |

### For non-logic comments:
1. Apply all fixes
2. Commit and push:
```bash
git add <changed files>
git commit -m "fix: [TICKET-KEY] address zip-agent review comments"
git push
```

### For logic comments:
1. Present each comment to the user with the file, line, and suggestion
2. Ask: "These are logic-related review comments. Should I apply any of these?"
3. Only fix after explicit user approval, then commit and push

If no zip-agent comments are found after 5 minutes → proceed to Phase 7.5.

---

## Phase 7.5: Manual CR Review & Fix

Poll for human review comments:
```bash
gh api repos/<owner>/<repo>/pulls/<pr_number>/reviews --hostname <github_hostname>
```

For each finding:
1. Identify severity (critical/medium/low/minor)
2. Locate relevant file(s)
3. Apply the fix
4. Note what changed

After fixes:
```bash
git add <changed files>
git commit -m "fix: [TICKET-KEY] address CR findings"
git push
```

**Severity priority:**
- Critical / Medium → must fix before merge
- Low → fix if straightforward, otherwise note in PR comment
- Minor → fix if trivial, otherwise acknowledge in PR comment

---

## Key Rules

- **Do NOT stop after coding.** After trycycle + Phase 5 validation pass, automatically commit, push, and open the PR without asking.
- Always display the PR URL in **bold orange** (ANSI `\033[1;38;5;208m`) via bash `printf` so the user can immediately see it.
- Use `architecture.md` as implementation contract
- Let trycycle handle the quality loop — don't shortcut it
- Always transition Jira ticket to In Progress at the start
- Always transition Jira ticket to Code Review after PR is created
- Always follow the project's existing branch and commit naming conventions
- Stage only the files this ticket touched — never `git add -A`
- Never force-push, never skip hooks (`--no-verify`), never amend published commits
- If UI: never start the dev server (app is already running)
- If Backend: never auto-run database migrations
- Always search canonical repos and internal docs during Phase 3 context gathering
