Invoke the doc-updater agent to sync documentation with the current codebase state.

Process:
1. Read source-of-truth files: `package.json`, `.env.example`, route files, JSDoc
2. Generate/update script reference tables
3. Generate/update environment variable documentation
4. Update `docs/CONTRIBUTING.md` with current setup and testing procedures
5. Update `docs/RUNBOOK.md` with deployment and operational procedures
6. Flag documentation files not updated in 90+ days

Rules:
- **Generate from code** — never manually edit auto-generated sections
- **Preserve manual prose** — only update `<!-- AUTO-GENERATED -->` sections
- **Don't create new doc files** unless explicitly requested

Scope: $ARGUMENTS (default: full project docs)
