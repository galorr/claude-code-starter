---
name: prompt-engineer
description: Design, optimize, and refine prompts to get the best possible responses from AI language models. Use this skill when the user wants to write, improve, or debug a prompt, create a system prompt, optimize AI instructions, or improve how an LLM responds to their requests. Trigger on "write a prompt for", "improve this prompt", "optimize this system prompt", "help me prompt engineer", "make this prompt better", "how do I get AI to do X", or any request where the goal is crafting effective LLM instructions. Apply structured prompt engineering methodology.
---

# Prompt Engineer — Systematic Prompt Design

Design and refine prompts that reliably elicit accurate, comprehensive, and efficient AI responses.

## Core Process

### 1. Deconstruct the Task
Before writing anything, understand:
- What is the **ultimate goal** of the AI output?
- What **constraints** apply? (length, format, tone, audience)
- What are the **explicit** requirements? The **implicit** ones?
- What does a **bad output** look like? (helps define success criteria)

### 2. Gather Context
Identify what background information the model needs:
- Domain knowledge
- User persona or intended audience
- Examples of good/bad outputs
- Format requirements
- Any special instructions or constraints

**Front-load all critical context** — models perform better with context at the start.

### 3. Draft the Prompt

Apply these techniques as appropriate:

#### Chain-of-Thought (Complex Tasks)
Break the task into sequential steps:
```
Think through this step by step:
1. First, identify X
2. Then, analyze Y
3. Finally, produce Z
```

#### Few-Shot Examples (Format/Style Consistency)
When the output format matters, show examples:
```
Here are two examples of the output format I want:

Input: [example input 1]
Output: [example output 1]

Input: [example input 2]
Output: [example output 2]

Now do the same for:
Input: [actual input]
```

#### Explicit Output Format
Specify exactly what you want:
```
Respond with a JSON object in this format:
{
  "summary": "...",
  "key_points": ["...", "..."],
  "confidence": 0-100
}
```

#### Constraints as Positive Instructions
Tell the model what TO do (not just what not to do):
- Instead of: "Don't be vague"
- Use: "Be specific with examples"

#### Persona vs. Instructions
Prefer clear instructions over role-playing when accuracy matters:
- Instead of: "You are an expert surgeon..."
- Use: "Provide clinical, evidence-based medical information with appropriate caveats..."

### 4. Self-Critique the Draft

Review against these criteria before finalizing:

| Criterion | Questions to Ask |
|-----------|-----------------|
| **Clarity** | Is every instruction unambiguous? Could it be misinterpreted? |
| **Completeness** | Does it include all necessary context and constraints? |
| **Efficiency** | Is it concise without losing important detail? |
| **Robustness** | Does it handle edge cases and misinterpretations? |
| **Alignment** | Does it precisely match the user's actual goal? |

### 5. Refine (2 Iterations Max)

After self-critique, make specific improvements:
- Reword ambiguous instructions
- Add missing context
- Adjust chain-of-thought steps
- Strengthen or relax constraints

**Two revision cycles are usually enough.** Don't over-engineer.

## Prompt Patterns

### System Prompt Structure
```
[Role/Context — what the model is doing and for whom]

[Core Instructions — what to do]

[Constraints — what to avoid or how to handle edge cases]

[Output Format — exactly what the response should look like]

[Examples — optional but powerful for format consistency]
```

### Instruction Clarity Checklist
- [ ] Every instruction has one interpretation
- [ ] Format is specified (if it matters)
- [ ] Edge cases are addressed
- [ ] Examples provided (if format is complex)
- [ ] Context front-loaded

### Common Improvements

**Vague → Specific:**
```
Before: "Write a good summary"
After: "Write a 2-3 sentence summary suitable for a non-technical executive, focusing on business impact rather than technical details"
```

**Instruction → Guided Reasoning:**
```
Before: "Analyze this code"
After: "Analyze this code by: (1) identifying potential bugs, (2) checking for security vulnerabilities, (3) suggesting performance improvements. For each issue, provide the line number and a recommended fix."
```

**Missing Format → Specified:**
```
Before: "List the pros and cons"
After: "List exactly 3 pros and 3 cons. Format as two sections with bullet points. Keep each point to one sentence."
```

## Output Format for This Skill

After applying the process, present:
1. **The refined prompt** — ready to use
2. **Techniques applied** — brief explanation of what was used and why
3. **Optional: alternative opening lines** — 2 variants to test

Keep explanations concise. The prompt itself is the primary deliverable.
