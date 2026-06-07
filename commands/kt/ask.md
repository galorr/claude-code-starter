---
name: kt:ask
description: Ask questions about a codebase using its knowledge-transfer documentation as context
---

Answer questions about this codebase using the generated knowledge-transfer documentation as context.

## Process

1. **Locate knowledge-transfer output** — Look for a `knowledge-transfer/` directory in the current working directory. If it doesn't exist, tell the user: "No knowledge-transfer output found. Run `/kt` (knowledge-transfer skill) first to generate documentation."

2. **Load cross-cutting context** — Read these files if they exist (skip any that don't):
   - `knowledge-transfer/components/_architecture-overview.md`
   - `knowledge-transfer/components/_dependency-graph.md`
   - `knowledge-transfer/components/_api-surface.md`
   - `knowledge-transfer/components/_data-models.md`
   - `knowledge-transfer/components/_conventions.md`
   - `knowledge-transfer/components/_onboarding-paths.md`
   - `knowledge-transfer/.manifest.json` (for metadata and unit listing)

3. **Selective component loading** — Based on the user's question, identify which component docs are most relevant:
   - If the question mentions a specific component/service/module name, read that component's doc from `knowledge-transfer/components/<slug>.md`
   - If the question is about dependencies or architecture, the cross-cutting docs are sufficient
   - If the question is broad (e.g., "how does auth work?"), read the 3-5 most relevant component docs based on keyword matching against the manifest unit list
   - Do NOT read all component docs upfront — only load what's needed to answer the question

4. **Answer the question** — Using the loaded documentation as context:
   - Provide a clear, direct answer
   - Reference specific component docs (e.g., "See `users-service.md` for details")
   - Include relevant file paths from the docs
   - Link to the HTML navigator when helpful (e.g., "Open `knowledge-transfer/index.html#users-service` for the full doc")

5. **Suggest follow-ups** — If the question opens up related areas, suggest 1-2 follow-up questions the user might want to ask.

## Rules

- Never guess or fabricate information not found in the knowledge-transfer docs
- If the docs don't contain enough information to answer, say so and suggest running `/kt` with a focus on the relevant directory
- Keep answers concise but thorough — reference the docs, don't repeat them verbatim
- If the manifest shows stale files (files changed since last run), mention this to the user

Question: $ARGUMENTS
