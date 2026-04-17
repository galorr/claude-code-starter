---
name: codepilot-ui
description: Orchestrate full end-to-end frontend feature development from a Jira ticket — retrieving specs, analyzing Figma designs, planning architecture, implementing UI, validating output, and committing code. Use this skill when the user provides a Jira ticket link and wants the full frontend development loop handled autonomously. Trigger on phrases like "implement this UI ticket", "build this frontend story", "start on this UI task", or when a Jira URL is pasted with frontend/UI context. This skill coordinates architecture, frontend implementation, and visual QA in sequence.
context: fork
agent: general-purpose
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, mcp__atlassian__getJiraIssue, mcp__atlassian__editJiraIssue, mcp__atlassian__addCommentToJiraIssue, mcp__atlassian__getTransitionsForJiraIssue, mcp__atlassian__transitionJiraIssue
---

# CodePilot UI — Autonomous Frontend Feature Development

Full development loop from Jira ticket to Git push.

## Required Inputs
- Jira ticket URL
- (Optional) User availability: `available` | `unavailable`

## Development Loop

### Phase 1: Retrieve & Parse Ticket

Fetch ticket from Jira MCP:
```
Fields to extract:
- ticket.title
- ticket.description
- ticket.acceptanceCriteria
- ticket.figmaLinks[]
- ticket.relatedComponents[]
```

If fields are missing and user is unavailable → send clarification question, poll for response every 30 seconds.

Transition ticket to **In Progress** using `mcp__atlassian__getTransitionsForJiraIssue` + `mcp__atlassian__transitionJiraIssue` (look for a transition named "In Progress" or "In Progress - Direct").

### Phase 2: Pull Figma Designs

For each URL in `ticket.figmaLinks[]`:
- Fetch full-page screenshots
- Capture developer frame links
- Store as `figmaContext`

Only fetch main frame views — no design tokens needed here.

### Phase 2.5: Search Golden Repos for Patterns

Before planning architecture, search known-good repositories for established frontend patterns.
(See: `skills/_shared/references/sourcegraph-search.md`)

1. Identify the key UI concepts in the ticket (e.g., "dialog", "form", "table", "signal", "reactive form", "lazy loading")
2. Search the frontend golden repo for each concept:
   - Use `mcp__github__search_code` or `gh search code` to find canonical implementations
   - Look for component structure, state management, SCSS organization, module boundaries
3. Search shared libraries for utilities or components that might already exist
4. Log what you found:
   ```
   Golden repo patterns found:
   - [pattern] from frontend-golden/[file] — [how it applies to this ticket]
   - [shared component] from shared-libs/[file] — [can reuse for X]
   ```

Store findings and use them to inform Phase 3 architecture planning.

### Phase 3: Architecture Planning

Switch to architect mode. Produce:

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

Write plan to `architecture.md`.

**If a major architectural decision is needed** (where to place feature, reuse vs extend, competing strategies) → present 2-4 options to user before proceeding.

### Phase 4: Setup Git Branch

Follow the project's branch naming convention. Check recent `git log --oneline` to determine the pattern, then:
```bash
git checkout staging
git pull
git checkout -b feat-<TICKET-KEY>
```

### Phase 5: Delegate UI Implementation

Invoke `/webcode` with:
```typescript
{
  ticketContext,
  figmaData: { frameUrls: ticket.figmaLinks },
  architecturePlan
}
```

WebCode must:
- Re-fetch each Figma frame before starting
- Implement with 100% design fidelity
- Use Angular 17 + modular SCSS
- Follow `architecturePlan` strictly
- Validate with `ng build`

### Phase 6: Output Validation

Invoke `/output-validator` with:
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

Returns: `{ status: "approved" | "rejected", issues[], recommendations[] }`

**If rejected** → return to Phase 5, fix issues, re-validate.

### Phase 7: Commit & Push (With Approval)

**Always ask the user before committing:**
> "Are you happy with the final implementation? Should I commit and push the code?"

If user is unavailable → send via notification channel, poll every 30s.

Only after explicit approval, follow the commit convention from recent `git log --oneline` (typically `feat: [TICKET-KEY] description`):
```bash
git add <specific files>
git commit -m "feat: [TICKET-KEY] <feature description>"
git push --set-upstream origin feat-<TICKET-KEY>
```

Then open a PR against `staging` using:
```bash
gh pr create --title "feat: [TICKET-KEY] ..." --body "..." --base staging
```

### Phase 8: CR Review & Fix

After the PR is created, poll for review comments:

```bash
gh api repos/<owner>/<repo>/pulls/<pr_number>/reviews --hostname <github_hostname>
```

Parse each review body for findings. For each finding:
1. Identify the severity (critical/medium/low/minor)
2. Locate the relevant file(s) in the codebase
3. Apply the fix
4. Note what was changed

After all findings are addressed:
```bash
git add <changed files>
git commit -m "fix: [TICKET-KEY] address CR findings"
git push
```

Re-fetch reviews to confirm no new blockers remain.

**Severity priority:**
- Critical / Medium → must fix before merge
- Low → fix if straightforward, otherwise note in PR comment
- Minor → fix if trivial, otherwise acknowledge in PR comment

## Key Rules

- Always get user approval before committing
- Use `architecture.md` as implementation contract
- Re-validate after every fix cycle
- Never push without user sign-off
- Never skip subcomponents defined in architecture plan
- Never start the dev server (app is already running)
- Always transition Jira ticket to In Progress at the start of Phase 1
- Always follow the project's existing branch and commit naming conventions
- Always search golden repos (frontend golden repo, shared libraries) before designing architecture
- Log all patterns and documentation referenced in the architecture plan

## Dependency Injection Note

Before injecting core services (LeadService, ApiService, etc.) into feature components:
- Analyze the dependency graph first
- Only inject services truly needed for core functionality
- Prefer event emission to parent components over direct service injection
- Avoids circular dependency chains between feature modules and core services
