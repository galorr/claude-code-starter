---
name: job-scanner-setup
description: Interactive setup for the job-scanner skill. Reads the user's uploaded CV, asks 5–7 questions about their target role / location / channel / schedule, generates a personalized job-scanner SKILL.md, and optionally registers it as a Cowork scheduled task. Trigger when the user says "set up the job scanner", "install job-scanner", "configure the daily job scan", or uploads a CV and mentions wanting daily job updates.
---

You are the SETUP HELPER for the `job-scanner` skill. Your job is to turn the
templated `skills/job-scanner/SKILL.md` (with `<<<PLACEHOLDER>>>` markers) into
a personalized SKILL.md for the current user, in one short interactive session.

This skill runs ONCE per user, not on a schedule. After this run, the
`job-scanner` skill itself runs daily.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — LOCATE THE TEMPLATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The template lives next to this setup skill:
  ../job-scanner/SKILL.md  (relative to this skill's directory)

If that path doesn't exist, search for `job-scanner/SKILL.md` under
`~/.claude/skills/` and the current working directory. If not found,
tell the user: "I need the job-scanner SKILL.md template — please install
the job-scanner skill first (it lives in the same repo) or paste the
template file path."

Read the full template into memory.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — READ THE USER'S CV
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If the user has uploaded a CV (look for a recent .pdf / .docx / .md file in
the conversation or in their uploads folder), read it.

If no CV is uploaded yet, ask the user once:
  "Drop your CV into the chat — I'll use it to populate your bio block.
   PDF, DOCX, and markdown all work. If you'd rather skip and fill the
   bio in manually, say 'skip CV'."

Extract from the CV:
  - Full name
  - Current role title and company
  - Years of experience
  - Tech stack (languages, frameworks, cloud)
  - Specialty / focus areas
  - Education
  - LinkedIn URL (look in the CV header)

If anything is unclear or missing, note it — you'll ask about it in STEP 3.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — INTERACTIVE QUESTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ask the user the following via AskUserQuestion. Batch related questions
into single AskUserQuestion calls (up to 4 per call). Use sensible
defaults from the CV where possible — only ask if you can't infer.

Q1 (always ask, even if CV gave a hint):
  "What role titles are you targeting? Pick the closest match — I'll
   include all related variants."
  Options:
    • Director of Engineering / Engineering Director / VP Engineering
    • Head of Engineering / Head of R&D / VP R&D
    • Engineering Manager / Senior EM / Group Manager R&D
    • Principal Engineer / Staff Engineer / Tech Lead
    • CTO / VP of Technology / Chief Architect
  (Multi-select is OK — they may target a band rather than a single title.)

Q2 (always ask):
  "Where are you looking? Where you actually want to work day-to-day."
  Options:
    • Single city or metro area (you'll specify)
    • Hybrid in a corridor (you'll specify the cities)
    • Anywhere remote (with timezone constraints)
    • Anywhere remote (no constraints)
  Then follow up with a free-text-style prompt for the actual cities /
  region.

Q3 (always ask):
  "Which Slack channel should the daily digest go to?"
  Options:
    • A dedicated personal channel I've created (you'll paste the channel ID)
    • A DM to myself
    • A shared channel with my career-search group
  Follow up by asking the user to paste the Slack channel ID (starts with
  C... for channels, D... for DMs). Tell them: in Slack, right-click the
  channel → View channel details → scroll to the bottom for the ID. Also
  ask for the channel name for display purposes (e.g. #my-job-search).

Q4 (always ask):
  "What time should it run each morning?"
  Options:
    • 06:00 (early bird)
    • 08:00 (recommended — most listings post overnight in EMEA / morning in US)
    • 10:00 (after coffee)
    • Custom time (you'll specify)

Q5 (always ask):
  "Should I include a watchlist of companies whose careers pages get
   checked directly every run?"
  Options:
    • Yes — I'll paste a list (one company per line)
    • Yes — but build it from my CV's prior employers + their competitors
    • No — broad market scan only
  If "yes — paste list", prompt the user for the list (free text) and
  ask for a 0–10 priority score per company (optional).

Q6 (always ask):
  "Do you have a Google Sheet of companies where someone you know can
   warm-intro your CV? (This is optional — the scanner adds a contact
   line and +0.5 score bonus for sheet companies.)"
  Options:
    • Yes — I'll paste the Google Sheet file ID
    • No — skip this feature
  If "yes", prompt for the file ID (the long string in the sheet URL
  between `/d/` and `/edit`).

Q7 (always ask):
  "Anything to add to the skip list — companies to NEVER report?
   (Defaults: your current employer.)"
  Free-text follow-up. Format: one company per line, optionally with a
  reason (e.g. "AcquiredCo (acquihired by current employer)").

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — FILL IN THE TEMPLATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Replace every `<<<PLACEHOLDER>>>` in the template with the gathered values.
Use the formats described in the job-scanner README's "Placeholder reference"
section. Specifically:

  - USER_BIO must be a bulleted list (one fact per line) — do not write a
    paragraph.
  - ROLE_TITLES must be one bullet per title with slash-separated synonyms
    on the same line.
  - LOCATION_DESC should explicitly mention which work modes are OK
    (on-site, hybrid, remote with HQ in corridor).
  - WATCHLIST: if the user opted out, write "(No watchlist configured — broad
    market scan only.)"
  - SKIP_LIST: always include the user's current employer first.
  - REGIONAL_JOB_BOARDS: infer from the user's location. If you don't know
    the regional boards, write "(No regional boards configured — relies on
    LinkedIn / Glassdoor / Google searches.)"

If the user opted OUT of the network sheet (Q6 answered "No"), REMOVE the
entire STEP 2.5 block from the template (everything between the STEP 2.5
header and the STEP 3 header) and replace it with:

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 2.5 — NETWORK SHEET SCAN:
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  (No network sheet configured — skipped. To enable later, set up a
  Google Sheet matching the schema in the job-scanner README and re-run
  job-scanner-setup.)

Also remove any 🤝 / "warm-intro" references in Message 2 and Message 3
formatting if the network sheet is disabled.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — WRITE THE PERSONALIZED FILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The destination depends on platform:

PLATFORM A — Cowork (preferred — supports scheduled tasks natively):
  Write to: ~/Documents/Claude/Scheduled/job-scanner/SKILL.md
  Create the directory if it doesn't exist.

PLATFORM B — Claude Code (CLI):
  Write to: ~/.claude/skills/job-scanner/SKILL.md
  Create the directory if it doesn't exist.

If you can't tell which platform you're on, ask the user once:
  "Are you on Cowork (the desktop app) or Claude Code (the CLI)?"

Write the personalized SKILL.md.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — REGISTER THE SCHEDULED TASK (Cowork only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If on Cowork, offer to register the scheduled task right now:

  "Should I register this as a scheduled task that runs every day at
   <<<RUN_TIME>>>?"
  Options:
    • Yes — register it (recommended)
    • No — I'll register it later via the /schedule skill

If yes:
  Call mcp__scheduled-tasks__create_scheduled_task with:
    - taskId: "job-scanner"
    - description: "Daily job scan — surfaces NEW <<<SENIORITY_LEVEL>>>
      openings in <<<TARGET_MARKET>>> to <<<SLACK_CHANNEL_NAME>>>."
    - cronExpression: build from RUN_TIME, e.g. "0 8 * * *" for 08:00 daily
    - prompt: the body of the personalized SKILL.md (NOT including the
      front-matter)
    - enabled: true

Confirm to the user:
  "Done — registered as scheduled task 'job-scanner'. Next run:
   tomorrow at <<<RUN_TIME>>>. The first run will write to
   <<<SLACK_CHANNEL_NAME>>>. To test it right now without waiting,
   say 'run the job-scanner task now'."

If Claude Code:
  Tell the user how to wire it up to their OS scheduler. Provide a
  copy-pasteable example for their platform (macOS launchd, Linux cron,
  or Windows Task Scheduler) that runs:
    claude -p "Run the job-scanner skill"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 7 — VERIFY & WRAP UP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Print a short summary back to the user:

  ✅ job-scanner is installed and configured.
  📍 Scanning: <<<TARGET_MARKET>>>, <<<LOCATION_KEYWORD>>>
  🎯 Target titles: <<<ROLE_TITLES summary>>>
  📨 Posting to: <<<SLACK_CHANNEL_NAME>>>
  🕐 Daily at: <<<RUN_TIME>>>
  🤝 Network sheet: <<<enabled / disabled>>>
  📁 Watchlist: <N> companies

  To change anything, re-run /job-scanner-setup or edit the SKILL.md at
  <<<destination path>>>.

  To trigger a test run right now: "run the job-scanner task now".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPLEMENTATION NOTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- ALWAYS use AskUserQuestion for the questions in STEP 3 — do not type the
  questions in chat. The tool renders them as proper chips/buttons in
  Cowork.
- Batch related questions into single AskUserQuestion calls (the tool
  supports up to 4 per call). Suggested batching:
    Batch A: Q1 (titles), Q2 (location)
    Batch B: Q3 (channel), Q4 (time)
    Batch C: Q5 (watchlist), Q6 (sheet), Q7 (skip list)
- For free-text follow-ups (channel ID, watchlist list, sheet ID, skip
  list), use a normal prompt in chat — AskUserQuestion is multiple-choice
  only.
- Validate the Slack channel ID format: should start with `C` (channel),
  `D` (DM), or `G` (group DM). If not, re-prompt.
- Validate the Google Sheet ID format: should be ~44 alphanumeric chars
  including dashes/underscores, no slashes. If the user pastes the full
  URL, extract the ID between `/d/` and `/edit`.
- Don't make the user fill in every advanced placeholder. Sensible defaults
  the user shouldn't be asked about:
    SENIORITY_LEVEL = "senior engineering leadership" (or pick from Q1)
    DNA_FIT_FACTORS = infer from the CV tech stack
    NETWORK_SHEET_TITLE = "Open positions"
    PRIMARY_TITLE = first title from Q1
    LOCATION_KEYWORD = first city/country from Q2
- If the user re-runs this setup later, detect the existing personalized
  SKILL.md and offer to "update existing config" or "start fresh". Don't
  blow away their watchlist edits silently.
- The user's MCPs must be set up before this skill runs. If Slack /
  Google Drive / WebSearch aren't available, warn the user but still
  generate the SKILL.md so they can fix the MCPs later.
