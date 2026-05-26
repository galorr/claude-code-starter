# Ticket Template

The writeup format Claudia uses when creating or updating tickets. The goal: someone who wasn't part of the investigation should be able to read this and understand both *what's broken* and *how to fix it* without additional context.

## Title

Format: `<service or area>: <short symptom> (<qualifier>)`

Good:
- `checkout-api: 500s on /submit when cart has >50 items (prod, started 2026-04-18 14:00 UTC)`
- `auth-service: intermittent token refresh failures after v3.2.0 deploy`

Bad:
- `bug in checkout` (no specificity)
- `checkout-api throws NullPointerException at CartValidator.java:142 when iterating over items collection and encountering a null SKU on the 51st element` (too long; save detail for the body)

## Body

Use these sections. Keep each one tight.

### Summary
One or two sentences. What's broken, for whom, since when.

### Symptom
The observable failure mode. Include:
- Error message or HTTP status, verbatim
- Who sees it (users, internal, monitoring)
- Reproduction steps if known

### Evidence
Bulleted. Each bullet is one piece of evidence with its source.

```
- Error spike in Datadog starting 2026-04-18 14:03 UTC: 350 errors/min vs baseline of 2/min. Query: service:checkout-api status:error @endpoint:/submit
- Deploy of v2.5.0 completed at 2026-04-18 13:58 UTC (5 min before spike)
- PR #4821 in v2.5.0 changed CartValidator to iterate items without null-guarding SKU
- Related: JIRA-8934 reported similar symptom in Q3 2025, fixed in CartValidator but regression reintroduced
```

### Root cause
The mechanism, not the symptom. 2-4 sentences describing *why* the symptom occurs. If the root cause isn't fully confirmed, say "likely root cause" and explain what would confirm it.

### Fix plan
High-level, not the code. Two to four bullets. If there's a clear small fix, say so. If it's larger, note the shape of the change. Flag any risks or open questions.

```
- Re-add null guard on SKU in CartValidator.validateItems (reverting the regression from PR #4821)
- Add a unit test covering the null-SKU case to prevent re-regression
- Consider: should a null SKU upstream be logged as a data issue rather than silently skipped?
```

### Workaround
If there's a way to unblock users while the fix ships, note it. If not, say "no workaround identified."

### Links
- Datadog dashboard or saved query
- Suspect PR(s)
- Related tickets
- Any relevant runbook

## For updates on existing tickets

Don't overwrite the original description — add a comment. Structure the comment as:

```
**Investigation update — <date>**

**New evidence:**
- ...

**Updated root cause:** <if changed from earlier hypothesis>

**Recommended next step:** <single clearest action>
```

## Priority / severity

Claudia doesn't assign priority unilaterally — that's the team's call. But in the writeup, note factors that inform it:

- Blast radius (one user vs. all users)
- Reversibility (data loss? auth bypass? just an annoying error?)
- Workaround available?
- Rate of occurrence

The goal is to give whoever triages enough information to set priority correctly, not to set it for them.
