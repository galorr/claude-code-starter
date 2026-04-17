Recommend the best model tier for the current task based on complexity and budget.

## Usage

`/model-route [task-description] [--budget low|med|high]`

## Routing Heuristic

| Model | When to use |
|-------|-------------|
| **haiku** | Deterministic, low-risk mechanical changes — formatting, simple renames, boilerplate generation |
| **sonnet** | Default for implementation, refactoring, debugging, most coding tasks |
| **opus** | Architecture decisions, deep code review, ambiguous/complex requirements, security audits |

## Output

- Recommended model
- Confidence level (high/medium/low)
- Reason this model fits the task
- Fallback model if first attempt is insufficient

## Examples

- "Fix this typo" → haiku (high confidence)
- "Implement JWT auth middleware" → sonnet (high confidence)
- "Design the data model for a multi-tenant SaaS" → opus (high confidence)
- "Review this for security issues" → opus (high confidence)

Arguments: $ARGUMENTS
