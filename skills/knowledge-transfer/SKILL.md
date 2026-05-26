---
name: knowledge-transfer
description: Analyze a codebase and generate a knowledge-transfer directory with per-component markdown docs and a master HTML navigator. Enriches with GitHub, Jira, and Confluence context.
when_to_use: "Trigger on 'knowledge transfer', 'generate codebase docs', 'document this repo', 'create knowledge base', 'onboarding docs'."
argument-hint: "[optional: specific directory to focus on]"
disable-model-invocation: false
context: fork
agent: general-purpose
effort: high
allowed-tools: Bash, Read, Write, Glob, Grep, Agent, mcp__github__get_file_contents, mcp__github__search_code, mcp__github__list_commits, mcp__github__list_issues, mcp__github__list_pull_requests, mcp__atlassian__searchJiraIssuesUsingJql, mcp__atlassian__getJiraIssue, mcp__atlassian__searchConfluenceUsingCql, mcp__atlassian__getConfluencePage, mcp__atlassian__getConfluenceSpaces, mcp__figma__generate_figma_design
---

# Knowledge Transfer — Codebase Documentation Generator

Analyze a codebase and produce a browsable knowledge base: per-component markdown docs enriched with GitHub, Jira, and Confluence context, plus a self-contained HTML navigator.

## Required Inputs
- A git repository (current working directory)
- Optional: a subdirectory path to focus analysis on (passed as `$ARGUMENTS`)

## Security — Forbidden Files

Never read or include content from these files. Skip them silently during analysis:
- `.env*`, `credentials.*`, `secrets.*`
- `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.p8`, `serviceAccountKey.json`
- `id_rsa`, `id_ed25519`, `id_ecdsa` (SSH private keys)
- `kubeconfig`, `.kube/config`, `.aws/credentials`, `.gcp/credentials.json`
- `*.token`, `*.secret`
- `.npmrc`, `.pypirc`, `.netrc`

---

## Workflow

### Phase 0 — Pre-flight

1. **Detect git remote** — run `git remote get-url origin` and extract `owner/repo` for GitHub MCP calls. If no remote exists, skip GitHub enrichment.
2. **Capture commit SHA** — run `git rev-parse HEAD` to get the current commit SHA. Store as `commitSha` for generating stable source permalinks. If the repo has a GitHub remote, the base URL for source links is `https://github.com/<owner>/<repo>/blob/<commitSha>/`.
3. **Check for prior run** — if `knowledge-transfer/.manifest.json` exists, read it and enter **incremental mode** (only re-analyze changed units).
4. **Scope** — if the user passed a directory argument via `$ARGUMENTS`, restrict all analysis to that subtree.
5. **Create output directories:**
   ```
   knowledge-transfer/
   knowledge-transfer/components/
   knowledge-transfer/diagrams/
   ```

### Phase 1 — Codebase Discovery & Classification

#### 1.1 Detect framework

Check for config files to identify the tech stack:

| File | Framework |
|------|-----------|
| `angular.json` | Angular |
| `nest-cli.json` or `@nestjs/core` in package.json | NestJS |
| `next.config.*` | Next.js |
| `nuxt.config.*` | Nuxt |
| `pyproject.toml` / `setup.py` | Python |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `pom.xml` / `build.gradle` | Java/Kotlin |
| `package.json` (generic) | Node.js |

Record the detected framework(s) for later use.

#### 1.2 Build directory tree

Run a directory listing excluding: `node_modules`, `dist`, `build`, `.git`, `coverage`, `knowledge-transfer`, `__pycache__`, `.next`, `.angular`.

#### 1.3 Identify analyzable units

Each unit becomes its own markdown file. Detect units by file naming patterns and directory structure:

| Pattern | Unit type |
|---------|-----------|
| `*.service.ts` | Service |
| `*.controller.ts` | Controller |
| `*.module.ts` | Module |
| `*.component.ts` | Component |
| `*.directive.ts` | Directive |
| `*.pipe.ts` | Pipe |
| `*.guard.ts` | Guard |
| `*.interceptor.ts` | Interceptor |
| `*.middleware.ts` | Middleware |
| `*.resolver.ts` | Resolver |
| `*.entity.ts` / `*.model.ts` | Model/Entity |
| `*.repository.ts` | Repository |
| `*.dto.ts` | DTO |
| `*.gateway.ts` | Gateway |
| `*.strategy.ts` | Strategy |
| `*.decorator.ts` | Decorator |
| `*.filter.ts` | Filter |
| `*.util.ts` / `*.helper.ts` | Utility |
| `*.config.ts` | Configuration |
| `__init__.py` with classes | Python module |
| `*.py` with `class` or `def` | Python module |
| `*.go` with `func` | Go package |
| `*.rs` with `pub fn` / `pub struct` | Rust module |
| Directories with `index.ts` / `index.js` | Module entry point |

Group units by directory proximity for batch processing.

#### 1.4 Incremental mode

If `.manifest.json` exists from a prior run:
- Compute SHA-256 hash of each source file
- Compare against stored hashes
- Skip units whose files are unchanged
- Report: `Incremental mode: X of Y units changed, re-analyzing those.`

#### 1.5 Scale check

If more than 100 analyzable units are detected, ask the user:

> **Found N analyzable units.** Choose analysis depth:
> 1. **Full** — analyze all N units (thorough but slow)
> 2. **Focused** — analyze only `src/` top-level modules and their direct children
> 3. **Shallow** — one paragraph per unit, no dependency tracing

Proceed with the user's choice.

### Phase 2 — External Context Gathering

Gather external context **upfront in batch** to avoid per-unit API calls. All MCP calls in this phase are optional — if a tool is unavailable, note the gap and continue.

#### 2.1 GitHub context

Using the `owner/repo` from Phase 0:

- **README**: fetch via `mcp__github__get_file_contents` (path: `README.md`)
- **Recent PRs**: fetch last 30 via `mcp__github__list_pull_requests`
- **Recent commits**: fetch last 50 via `mcp__github__list_commits`

Build a lookup map: `filePath → [{ type: "PR"|"commit", id, title, date }]`. To map PRs to files, use PR titles and branch names as hints (exact file mapping comes from commit paths).

#### 2.2 Jira context

Detect the Jira project key:
1. Check `CLAUDE.md` or `README.md` for project key mentions (pattern: `[A-Z]{2,}-\d+`)
2. Check recent branch names (pattern: `feature/PROJ-123-*`)
3. Derive from repo name or documentation
4. If none found, ask the user: "What's the Jira project key for this repo? (e.g., `PROJ`)"

Search recent tickets (last 90 days):
```
project = <KEY> AND updated >= -90d ORDER BY updated DESC
```

Build a lookup map: `keyword → [{ key, title, status }]` using ticket titles as keyword sources.

#### 2.3 Confluence context

Search for repo-related documentation:
- Query: repo name, detected framework, key directory names
- Fetch top 10 matching pages via `mcp__atlassian__searchConfluenceUsingCql`

Build a lookup map: `keyword → [{ title, url }]`.

### Phase 3 — Per-Unit Deep Analysis

Process units in batches of 3–5, grouped by directory proximity so related units share context.

For each unit:

#### 3.1 Read and parse

- Read all source files belonging to the unit
- Identify key constructs: classes, functions, decorators, endpoints, entities, config values
- Extract exported public interface (function/method signatures, class names)

#### 3.2 Trace dependencies

Use the appropriate import pattern based on the detected framework:

| Language | Outbound grep pattern |
|----------|----------------------|
| TypeScript/ES modules | `import.*from` |
| CommonJS (JS/TS) | `require\(` |
| Python | `^import ` / `^from .* import` |
| Go | `"module/path"` inside `import` blocks |
| Rust | `^use ` |
| Java/Kotlin | `^import ` |

- **Outbound**: grep for the language-appropriate import pattern in the unit's files → list what it depends on
- **Inbound**: grep across the codebase for imports/references to this unit → list what depends on it

#### 3.3 Enrich with external context

- Match file paths against the Phase 2 GitHub lookup → attach recent PRs and commits
- Match unit name and keywords against Phase 2 Jira/Confluence lookups → attach related tickets and wiki pages
- **On-demand Jira enrichment**: scan commit messages touching this unit's files for ticket references (regex: `[A-Z]{2,}-\d+`). Collect all references across all units first, then deduplicate against the Phase 2 batch and fetch missing tickets in a single pass via `mcp__atlassian__getJiraIssue`. If more than 50 new ticket references are found, skip on-demand enrichment and note the gap in the output. This avoids unbounded per-unit API calls on large codebases.

#### 3.4 Generate markdown

Write `knowledge-transfer/components/<unit-slug>.md` using the template from `references/component-template.md`.

The `<unit-slug>` is the unit name in kebab-case (e.g., `users-service`, `auth-module`, `checkout-controller`).

**Source deep links:** If a GitHub remote and `commitSha` were captured in Phase 0, convert file paths in the "Key Files" table and any line references into GitHub permalink URLs:
- File path: `[src/users/users.service.ts](https://github.com/<owner>/<repo>/blob/<commitSha>/src/users/users.service.ts)`
- Line reference: `[line 45](https://github.com/<owner>/<repo>/blob/<commitSha>/src/users/users.service.ts#L45)`

If no git remote was detected, keep file paths as plain text (backtick-quoted paths without links).

#### 3.5 Track patterns

While analyzing each unit, note recurring code structures for convention extraction in Phase 4:
- Naming patterns (file naming, class naming, method naming)
- Error handling approaches (custom exceptions, try/catch patterns, error wrapping)
- Dependency injection style (constructor, property, module-level)
- Testing patterns (describe/it structure, mocking approach, setup patterns)
- Logging patterns (logger instance, structured fields, log levels used)
- API response patterns (envelope format, error shape, pagination style)
- Configuration access patterns (env vars, config service, constants)

Store observations as a running list (pattern → count of units using it). This feeds Phase 4's `_conventions.md`.

#### 3.6 Track coverage flags

For each unit, record coverage indicators:
- `hasGithubContext` — true if any PRs or commits were linked from Phase 2.1
- `hasJiraContext` — true if any Jira tickets were linked
- `hasConfluenceContext` — true if any Confluence pages were linked
- `hasDiagram` — true if a data flow diagram was generated (any tier)

Store these flags in the manifest unit entries for health metrics calculation in Phase 6.

#### 3.7 Update manifest

After each batch, update `knowledge-transfer/.manifest.json` with file hashes, timestamps, and coverage flags for crash-safe incremental support.

#### 3.8 Progress reporting

After each batch, output:
```
[12/47] Analyzed: users-module, users-service, users-controller
```

### Phase 4 — Cross-Cutting Documents

Generate these from the synthesized per-unit data. Write each to `knowledge-transfer/components/`.

#### `_architecture-overview.md`
- High-level architecture description
- **Layer diagram** — use the diagram fallback chain (see below)
- Entry points (main files, bootstrap, app module)
- Data flow overview
- Framework and major dependency versions

#### `_dependency-graph.md`
- **Dependency diagram** — use the diagram fallback chain (see below) to generate a flowchart showing unit relationships
- Identify circular dependencies and flag them
- Group by layer/directory

#### `_api-surface.md` (only if HTTP endpoints detected)
- Table of all API endpoints: method, path, controller, handler function, auth guards
- Grouped by controller/resource

#### `_data-models.md` (only if database entities detected)
- Table of all entities: name, table, key columns, relationships
- **ER diagram** — use the diagram fallback chain (see below)

#### `_conventions.md`
Synthesize the pattern observations collected during Phase 3.5 into a conventions reference document. For each detected convention:

- **Naming conventions** — file naming patterns, class/function naming, variable naming (e.g., "Services suffixed with `Service`, DTOs with `Dto`")
- **Error handling** — how errors are caught, thrown, wrapped, custom exception classes
- **Dependency injection** — constructor injection vs property injection, circular dependency patterns
- **Testing patterns** — test file naming (`*.spec.ts` vs `*.test.ts`), mocking approaches, test structure
- **Logging** — logger instantiation, structured vs unstructured, log levels
- **Code organization** — barrel exports, index files, module boundaries, feature-folder structure
- **API patterns** — response envelope format, pagination approach, error response structure, validation
- **Configuration** — how env vars are accessed, config module usage, defaults

Each convention entry includes:
1. **Pattern** — what the convention is
2. **Frequency** — how many units follow it (e.g., "42 of 47 units")
3. **Example** — 1-2 short code snippets demonstrating the pattern (with file path attribution)
4. **Exceptions** — units that deviate (potential tech debt or intentional variance)

#### `_onboarding-paths.md`
Generate role-based learning paths — ordered reading sequences through the documented units to help new team members ramp up efficiently.

**Detect applicable roles from codebase structure:**
- **Backend onboarding** — if NestJS/Express/Go/Python backend: start with app module/main entry point → core services → controllers → models → utilities
- **Frontend onboarding** — if Angular/React/Next.js: start with app component/routing → core modules → shared components → services → utilities
- **Full-stack onboarding** — combine both paths, starting with architecture overview
- **API consumer onboarding** — start with `_api-surface.md` → relevant controllers → DTOs → auth guards
- **Data onboarding** — start with `_data-models.md` → entities → repositories → services that use them

**Each path includes:**
1. Title and one-sentence description of who it's for
2. 5-10 docs in recommended reading order
3. A brief note (one line) for each doc explaining why it's in this sequence

**"Start here" tagging:**
Tag the top 5-10 most critical docs for any new joiner. Critical docs are determined by:
- Main entry point module (highest structural importance)
- `_architecture-overview.md` (always critical)
- Most-depended-on service (highest inbound dependency count from Phase 3.2)
- Most-changed unit (highest number of recent PRs/commits from Phase 2.1)
- Any unit with the richest external context (most Jira tickets + PRs linked)

Mark these with `<!-- start-here -->` in their markdown, and include a `"startHere": true` flag in the HTML navigator's docs-data entries.

### Diagram Fallback Chain

Whenever a diagram is needed (architecture layers, dependency graph, ER diagram, per-unit data flow), follow this three-tier fallback:

1. **Claude Design (preferred)** — Generate a self-contained HTML file in `knowledge-transfer/diagrams/` with the diagram rendered visually using inline SVG or Mermaid.js (embed the Mermaid library via a `<script>` tag from a CDN, or render to SVG at generation time). The HTML file must work offline via `file://`. Link to it from the markdown doc. Name the file after the diagram (e.g., `architecture-layers.html`, `dependency-graph.html`, `users-service-dataflow.html`).

2. **Figma Design (fallback)** — If generating a standalone HTML diagram is not feasible (e.g., the diagram is too complex to render cleanly in HTML), use `mcp__figma__generate_figma_design` to create the diagram as a Figma design and embed the returned Figma link in the markdown doc.

3. **ASCII (last resort)** — If neither of the above is available (no Figma MCP connected, no CDN access), fall back to an ASCII/textual diagram inline in the markdown.

Always create the `knowledge-transfer/diagrams/` directory in Phase 0 if using tier 1 or 2.

### Phase 5 — Master HTML Navigator

Generate `knowledge-transfer/index.html` — a self-contained single HTML file with no external dependencies that works via `file://` protocol.

Build the HTML following the template guidance in `references/html-template.md`.

**Content embedding:**
- Read all generated markdown files from `knowledge-transfer/components/`
- Embed their content as a JSON array inside a `<script>` tag:
  ```json
  [
    { "slug": "users-service", "title": "Users Service", "category": "Service", "content": "..." },
    { "slug": "_architecture-overview", "title": "Architecture Overview", "category": "Overview", "content": "..." }
  ]
  ```

**Content embedding:**

Also embed metadata, coverage metrics, and graph data as additional `<script type="application/json">` blocks:
- `id="docs-meta"` — repo URL, commit SHA, framework, timestamp
- `id="coverage-data"` — coverage percentages from Phase 3.5 / Phase 6.1
- `id="graph-data"` — simplified node/edge structure from Phase 5.5 knowledge graph (just `{id, label, category}` per node, `{source, target, type}` per edge)

**Required features:**
- Left sidebar with category-grouped navigation (Overview, Service, Controller, Module, etc.)
- Full-text search input that filters the sidebar list in real-time
- Category filter chips (click to show/hide categories)
- Dark/light mode toggle (respects `prefers-color-scheme`, stores preference in `localStorage`)
- Hash-based URL routing (`#users-service` navigates to that doc)
- Responsive layout (sidebar collapses on mobile)
- Inline markdown-to-HTML renderer (~50 lines JS) supporting: headings, bold, italic, code blocks, inline code, tables, lists, links, horizontal rules
- Modern minimal design: system font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`), clean sidebar, styled code blocks with monospace font, comfortable reading width
- Interactive dependency graph view with clickable nodes that navigate to component docs
- Coverage dashboard bar showing documentation health metrics
- Learning Paths panel in sidebar with ordered reading sequences and "Start here" badges on critical docs

### Phase 5.5 — Knowledge Graph Export

Generate `knowledge-transfer/knowledge-graph.json` — a structured entity-relationship graph consumable by external tools (graph databases, visualization tools, IDE plugins).

#### Schema

```json
{
  "meta": {
    "repo": "<owner/repo>",
    "commitSha": "<sha>",
    "generatedAt": "<ISO timestamp>",
    "framework": "<detected framework>"
  },
  "nodes": [
    {
      "id": "users-service",
      "label": "Users Service",
      "type": "Service",
      "files": ["src/users/users.service.ts"],
      "directory": "src/users",
      "publicMethods": ["findAll", "findById", "create", "update"],
      "hasTests": true,
      "endpoints": ["/users", "/users/:id"],
      "coverage": { "github": true, "jira": true, "confluence": false }
    }
  ],
  "edges": [
    {
      "source": "users-controller",
      "target": "users-service",
      "type": "imports",
      "label": "UsersService injection"
    }
  ]
}
```

#### Edge types

`imports`, `extends`, `implements`, `calls`, `injects`, `emits`, `subscribes`

#### Build process

- **Nodes**: one per unit from Phase 3 analysis. Populate `id` (slug), `label` (title), `type` (category), `files`, `directory`, `publicMethods` (from Phase 3.1 public interface extraction), `hasTests` (true if any spec/test file in the unit's file list), `endpoints` (from controllers), `coverage` (from Phase 3.5 flags).
- **Edges**: from Phase 3.2 dependency tracing. Each outbound dependency becomes an edge from the current unit to the target. Determine edge type from the import/usage pattern:
  - Constructor injection → `injects`
  - `extends` keyword → `extends`
  - `implements` keyword → `implements`
  - `emit` / `publish` patterns → `emits`
  - `subscribe` / `on` patterns → `subscribes`
  - Default (standard import) → `imports`

### Phase 6 — Manifest & Summary

#### 6.1 Write final manifest

Write `knowledge-transfer/.manifest.json`:
```json
{
  "generated": "<ISO timestamp>",
  "generator": "knowledge-transfer-skill",
  "commitSha": "<sha from Phase 0>",
  "repoUrl": "https://github.com/<owner>/<repo>",
  "scope": "<full | directory path>",
  "framework": "<detected framework>",
  "units": {
    "<unit-slug>": {
      "files": ["src/users/users.service.ts"],
      "hashes": { "src/users/users.service.ts": "<sha256>" },
      "analyzedAt": "<ISO timestamp>",
      "coverage": {
        "hasGithubContext": true,
        "hasJiraContext": true,
        "hasConfluenceContext": false,
        "hasDiagram": true
      }
    }
  },
  "externalContext": {
    "github": true,
    "jira": true,
    "confluence": false
  },
  "outputs": {
    "knowledgeGraph": true,
    "htmlNavigator": true
  },
  "coverage": {
    "totalSourceFiles": 156,
    "documentedFiles": 142,
    "documentedPct": 91.0,
    "withGitHubContext": 38,
    "withGitHubContextPct": 80.8,
    "withJiraContext": 23,
    "withJiraContextPct": 48.9,
    "withConfluenceContext": 0,
    "withConfluenceContextPct": 0.0,
    "withDiagrams": 12,
    "withDiagramsPct": 25.5,
    "staleFiles": 0
  }
}
```

#### 6.2 Gitignore suggestion

Ask the user:
> **Add `knowledge-transfer/` to `.gitignore`?** Generated docs are usually excluded from version control. (y/n)

If yes, append `knowledge-transfer/` to `.gitignore`. If no, do nothing. **Never auto-modify `.gitignore` without asking.**

#### 6.3 Output summary

```
Knowledge Transfer complete.

  Units documented:  47
  Categories:        12 Services, 8 Controllers, 6 Modules, 5 Models, 4 Utilities, ...
  Cross-cutting:     architecture-overview, dependency-graph, api-surface, data-models, conventions, onboarding-paths
  External context:  GitHub (30 PRs, 50 commits), Jira (23 tickets), Confluence (skipped)

  Coverage:
    Files documented:     142/156 (91%)
    With GitHub context:   38/47 units (81%)
    With Jira context:     23/47 units (49%)
    With diagrams:         12/47 units (26%)
    Stale files:           0

  Knowledge graph:   knowledge-transfer/knowledge-graph.json
  Open in browser:   knowledge-transfer/index.html
```

---

## Key Rules

- **Human-facing output.** Every markdown file and the HTML navigator are for humans — engineers reading docs, not Claude agents processing instructions. Write in clear prose, not agent directives.
- **No secrets.** Never read or embed content from forbidden files (see Security section above).
- **Incremental by default.** If `.manifest.json` exists, only re-analyze changed files. The user can force a full re-run by deleting `.manifest.json`.
- **MCP tools are optional.** The skill works without any MCP connections — it just produces richer output when they're available. Never fail because a tool is missing; note the gap and continue.
- **Don't modify source code.** This skill is read-only against the target codebase. The only files it writes are inside `knowledge-transfer/`.
- **Crash-safe.** Update `.manifest.json` after each batch so a partial run can be resumed incrementally.
- **Ask before modifying shared files.** The only shared file this skill might touch is `.gitignore`, and only with explicit user consent.

---

## References

- `references/component-template.md` — markdown template for per-unit documentation files
- `references/html-template.md` — HTML navigator template and implementation guidance
- `references/conventions-template.md` — template for the `_conventions.md` cross-cutting document
