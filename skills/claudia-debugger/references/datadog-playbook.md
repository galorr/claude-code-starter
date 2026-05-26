# Datadog Playbook

How Claudia uses Datadog evidence. Read this when the investigation involves production symptoms, latency, error rates, or anything with a timestamp.

## Time-window discipline

The single most common mistake is querying the wrong time window. Before running any Datadog query:

1. Pin down the **incident window** — when did the symptom start, when did it stop (or is it still ongoing)?
2. Also grab a **baseline window** — the same duration, 24h or 7d earlier, when things were working. You need the comparison.
3. Query both windows. "Errors spiked" is only meaningful relative to normal.

If the user gives you a vague window ("sometime this morning"), narrow it down with an initial broad query, then zoom in.

## Query order

Run these in parallel when the symptom is unclear:

1. **Error logs** filtered by service — `service:<name> status:error` over the incident window. Look at the top error messages, not just the count.
2. **APM traces** for the affected service — sort by duration desc and by error=true. A single slow trace often reveals more than 1000 log lines.
3. **Metrics** for the obvious suspects — request rate, error rate, p50/p95/p99 latency, CPU, memory, DB connections. Look for step changes aligned with the incident start.

Correlate across the three. An error spike with no latency change suggests a logic bug or bad input; an error spike alongside latency degradation suggests a downstream dependency or resource exhaustion.

## Trace-to-log correlation

When you find a suspicious trace, pull the logs correlated with that trace ID. Datadog links them. The logs inside a failing trace usually tell you the exact line that blew up — far more useful than searching logs independently.

## What to extract and record

For each piece of Datadog evidence cited in your writeup, capture:

- The **trace ID** or **log query** (so someone can reproduce your finding)
- The **exact timestamp** of the first occurrence
- The **error message or metric value** verbatim — don't paraphrase

## Red flags worth chasing

- Error rate climbs gradually over hours rather than spiking — suggests a memory leak, connection pool exhaustion, or slowly filling queue.
- Errors concentrated on one host/pod — suggests a bad instance, not a code bug. Check if a rolling deploy is in progress.
- Errors only on one region/AZ — suggests infra or a regional dependency.
- Latency spike with no error rate change — suggests a slow downstream service; errors will follow once timeouts trip.
- Perfect periodicity (every N minutes) — suggests a cron job, retry storm, or a health check gone wrong.

## When Datadog isn't enough

Datadog tells you *what* and *when*. For *why* you usually need to cross-reference with GitHub (what deployed around that time?) and Jira (has this happened before?). A symptom timeline without a code context is only half an investigation.
