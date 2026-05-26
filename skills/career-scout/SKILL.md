---
name: career-scout
description: >
  Career intelligence for any professional, role, or seniority — engineers, managers,
  designers, PMs, marketers, sales, data, finance, ops, and more. Trigger when the user
  uploads a CV or resume, shares a LinkedIn URL, shares a company URL or name and asks
  about fit or ranking, says "should I apply here", "rank this company", "help me prepare
  for an interview", or "research this company". Two workflows: (1) Company ranking — any
  company URL or name gives an instant 1-10 score across growth, equity, role fit, and
  culture, plus the open position and apply link; (2) Interview prep — given the position
  and interviewer, produces predicted questions, STAR stories, questions to ask, and a
  closing line. On first run a short setup reads the CV and asks 4 questions. The target
  position comes from the user's CV — never assumed. Once the profile is set, any company
  link triggers ranking immediately. Use Hebrew OR English only — never mix.
---

# Career Scout

A career intelligence skill for job seekers of any profession and any seniority level.
It reads the candidate's CV to understand what role they are targeting, then ranks
companies for fit and builds tailored interview preparation guides.

The skill works for anyone: a junior frontend developer, a product manager, a UX designer,
a finance analyst, a sales lead, a VP of Marketing, a data scientist, a customer success
manager — the position is always derived from the candidate's own CV and stated goals,
never assumed.

The skill has two core workflows — **Company Ranking** and **Interview Preparation** —
preceded by a one-time **Profile Setup**.

---

## Mode 1 — Profile Setup (first time only)

Triggered when: user uploads CV/resume, shares LinkedIn URL, or says "help me find a job".

### Step 1A — Read the CV or LinkedIn

**If CV/resume uploaded (PDF or DOCX):**
Read it using the appropriate file tool. Extract silently:
- Full name, current title, current company
- **Profession / function** (e.g. software engineering, product, design, marketing,
  sales, data, finance, operations, HR, legal, etc.)
- **Seniority level** (intern, junior, mid, senior, lead, manager, director, VP, C-level)
- Years of experience and career trajectory
- Skills, tools, and domain expertise relevant to their field
  (for an engineer: languages/frameworks/cloud; for a marketer: channels/tools/campaigns;
  for a designer: tools/methods/portfolio; adapt to the profession)
- Team / org size managed, if any
- Key achievements with numbers (%, $, x, scale)
- Education and notable background
- Location

**If LinkedIn URL shared:**
Web-fetch the profile page. Extract the same fields above from the page content.
If the page is blocked, ask the user to paste their LinkedIn summary or upload their CV instead.

**The target position is inferred from the CV** — current title and trajectory point to
the natural next role(s). Confirm it with the user in Step 1B rather than assuming.

### Step 1B — Ask Targeted Questions

After reading the profile, ask 3-4 focused questions using the ask_user_input_v0 widget.
Keep it conversational — one widget call with all questions together.

**Critical rule — "Other" option:**
Every single question MUST include "Other — I'll type it" as the last option.
The predefined choices are starting points, not a cage. When the user picks
"Other — I'll type it" on any question, immediately follow up in plain text:
"What are you looking for?" and use their exact free-text answer in the profile.
Never assume or rephrase — store their words verbatim.

Always ask these 4 questions. **Build question 1 dynamically from the CV** — offer the
candidate's current-level role and the natural next step up, based on what the CV shows.

1. **Target role** (single select) — generate options from the candidate's CV:
   - [Their current role title — "stay at my level, better company"]
   - [The natural next step up from their current role]
   - [A lateral or adjacent role their background supports, if relevant]
   - Open to a range of roles at my level
   - Other — I'll type it

   Example for a "Senior Product Manager": options would be Senior Product Manager,
   Group Product Manager / Lead PM, Director of Product, Open to a range, Other.
   Example for a "Frontend Developer": options would be Frontend Developer,
   Senior Frontend Developer, Full-stack Developer, Open to a range, Other.

2. **Location preference** (single select):
   - My current city only
   - My metro area / commutable distance
   - Anywhere in my country
   - Open to remote
   - Other — I'll type it

3. **Company stage preference** (single select):
   - Pre-IPO startup (max equity upside)
   - Public company (stability + liquidity)
   - Growth stage Series B–D
   - Any — just show me the best fit
   - Other — I'll type it

4. **Preferred industry / domain** (single select) — adapt the examples to the
   candidate's field, but always keep these broad buckets:
   - Same industry as my current company
   - B2B SaaS / software
   - A specific industry I'll name
   - Any industry — fit matters more than sector
   - Other — I'll type it

**After the widget:** for every question where the user chose "Other — I'll type it",
ask that follow-up in plain text before proceeding to Step 1C.
Collect all answers (predefined + free text), then build the profile.

### Step 1C — Build and Confirm Candidate Profile

Combine CV data + user answers into a structured profile. Show the user a 5-line summary
and ask: "Does this look right?" before proceeding.

Store the profile — it will be used for ALL subsequent company rankings and interview prep.

Profile fields to store:
```
name, current_title, current_company, profession, seniority_level, years_exp,
skills[], tools[], domain_expertise[], managed_team_size, key_achievements[],
target_titles[], target_location, preferred_stage, preferred_industry,
education, notable_background
```

---

## Mode 2 — Company Ranking

Triggered when: user shares ANY company URL or company name after profile is set up.
This is the core daily-use mode. The user just drops a URL — the skill does everything.

### Step 2A — Research the Company

Web-search and/or web-fetch the company's website. Collect:
- What they do (product, customers, market)
- Employee count and growth trajectory
- Funding stage, last round, valuation, investors
- Revenue / ARR if public
- YoY growth rate
- Recent news (layoffs, new funding, IPO plans, leadership changes)
- Glassdoor score (specifically the candidate's country/office if available)
- Local presence relevant to the candidate's target location: office size, growth plans
- Whether the company has roles in the candidate's profession
- Open positions matching the candidate's target titles

Read `references/scoring-methodology.md` for the full scoring rubric.

### Step 2B — Score the Company (1–10)

Score on 4 weighted criteria:

| Criterion | Weight | What to assess |
|---|---|---|
| Growth & Momentum | 30% | YoY revenue/ARR growth, funding recency, headcount growth |
| Equity Potential | 25% | Pre-IPO upside, public stock trajectory, PE exit timeline |
| Role Fit | 25% | Match between the candidate's profession, seniority, skills, and domain and what this company needs |
| Culture | 20% | Glassdoor score (candidate's region if available), layoff history, management reviews |

**Score interpretation:**
- 8–10: Strong fit — prioritize
- 5–7: Worth considering — has caveats
- Below 5: Low priority — flag reasons clearly

**Red flags that cap score at 5:**
- 3+ layoff rounds in 3 years
- Stock down 80%+ from peak
- Revenue growth under 5% for 2 years
- Glassdoor below 3.0
- C-suite mass exodus (3+ in one year)

### Step 2C — Find Open Positions

Search for open positions matching the candidate's target titles and profession:
- Check the company's careers page directly
- Search LinkedIn for company + target title
- Find the **direct apply link** (the actual submit-CV page, not homepage)
- Note if it's proactive outreach territory (no open role but strong fit)

If proactive: find the name and title of the most relevant hiring lead for the
candidate's function (e.g. the engineering lead for an engineer, the Head of Design
for a designer, the VP Marketing for a marketer, the hiring manager for that team).

### Step 2D — Deliver the Company Report

Format (Hebrew or English — match the user's language):

```
## [COMPANY NAME]  [X.X/10]
Location | ~[N] employees | [Stage] | [Industry]

### Why this score
Growth ([score]/10): [2-line explanation]
Equity ([score]/10): [2-line explanation]
Role Fit ([score]/10): [2-line explanation — specific to THIS candidate's profession,
                        seniority, and background]
Culture ([score]/10): [2-line explanation]

### Why apply
[3 bullet points specific to the candidate]

### Watch out for
[2-3 honest red flags or fit gaps]

### Open Position
[ROLE TITLE] — [direct apply link]
OR
No open role — reach out directly to [NAME], [TITLE]

### Bottom line
[2-sentence verdict — is it worth pursuing right now?]
```

---

## Mode 3 — Interview Preparation

Triggered when: user says "help me prepare for an interview", "I have an interview with [name]",
"interview prep for [company]", or after a high-scoring company ranking.

### Step 3A — Gather Interview Details

Ask with the ask_user_input_v0 widget:

1. **Interview stage** (single select):
   - First interview — introductory
   - Second interview — deep dive
   - Final interview / offer stage
   - Not sure
   - Other — I'll type it

2. **What matters most to you from this interview** (single select):
   - Impress and advance the process
   - Understand if this is the right place for me
   - Discuss terms and expectations
   - All of the above
   - Other — I'll type it

Then ask in plain text (always free text — names can't be predefined):
"What's the interviewer's name and title? (e.g. 'Dana Levi, VP Marketing')"

If user chose "Other — I'll type it" on any widget question, follow up before proceeding.

### Step 3B — Research the Interviewer

Web-search the interviewer's name + company. Collect:
- Current title and role at the company
- Career history (previous companies, titles)
- Professional background and specialties
- Any public content (talks, posts, articles)
- Working-philosophy signals visible from their background
- Certifications or credentials that signal their values

Read `references/interview-frameworks.md` for question banks and STAR guidance.
The reference file has question sets for multiple professions and seniority levels —
select the section that matches the candidate's profile.

### Step 3C — Build the Interview Prep Guide

Deliver a full guide in this structure:

**1. Who You're Meeting**
3-paragraph profile of the interviewer — background, what they care about,
how to connect with them based on their history.

**2. What They Will Ask You**
5-6 predicted questions based on their role + the candidate's profession + seniority +
the JD, with:
- The question as they'd phrase it
- Why they're asking it (what they're really testing)
- A ready-made answer framework using the candidate's actual experience

**3. Your Stories — Ready to Tell**
A table of 5-6 STAR stories the candidate should prepare, mapped to likely topics:
| Topic | Story to use | Key numbers to mention |

**4. What to Highlight — The 3 Things**
The 3 specific points from the candidate's background that are most relevant
to THIS interviewer and THIS company. Formatted as talking points.

**5. Your Questions for Them**
4 strong questions to ask the interviewer, with:
- The question
- Why it's smart to ask this (what it signals)
- What a good answer looks like vs. a red flag

**6. Closing Line**
A specific 2-3 sentence closing statement tailored to the company and interviewer —
what to say at the end of the interview to leave a strong impression.

---

## General Guidelines

**Role-agnostic:** This skill works for any profession and any seniority. Always derive
the target role from the candidate's CV and their answer to question 1 — never assume
they are an engineer, a manager, or any particular function.

**Language:** Always Hebrew OR English — never mix. Match the user's language.
If unclear, ask once at the start.

**"Other" answers:** Always respected verbatim — never rephrase or normalize the user's
free-text input. If they write something unusual, use it as-is in the profile.

**Tone:** Direct, honest, no fluff. Flag red flags clearly — don't soften bad news.

**Specificity:** Every insight must be specific to THIS candidate — use their actual
skills, their actual achievements, their actual background. Generic advice is useless.

**Numbers:** Always use numbers — years, percentages, employee counts, funding amounts.

**Profile persistence:** Once the candidate profile is set up, never ask for it again.
Use it silently in all subsequent rankings and interview preps.

**Proactive outreach:** Many roles are not posted. Always include a proactive
outreach path for high-scoring companies with no open position.

**Fit gaps:** When the candidate's background differs from what the company needs, name it
clearly and suggest a bridge — how to position the transferable skills.

---

## Reference Files

Read these when needed — do not load all at once:

- `references/scoring-methodology.md` — Full scoring rubric for company ranking, any role
- `references/interview-frameworks.md` — Question banks by profession + seniority, STAR templates, closing lines
- `references/known-companies-israel.md` — Optional: pre-researched Israeli tech companies; always verify with web search
