# job-scanner

A daily personalized job-market scanner. Every morning, it searches LinkedIn, Glassdoor, regional job boards, VC portfolio boards, remote-work boards, and a user-supplied watchlist of companies. It deduplicates against prior runs, verifies every apply link is live, and posts a ranked digest of NEW openings to a Slack channel.

Born out of a real daily-driver use case — see the original looker scheduled task that's been running since early 2026.

## What you get

Every morning at the time you configure, a thread arrives in your chosen Slack channel:

```
@channel Daily Job Scan — Wednesday, 2026-05-27
9 new positions found.

  ↪ Director of Engineering, AI Quality — NICE  ⭐ 7.5/10
    📍 Ra'anana (hybrid)  |  👥 ~10,000 employees  |  Enterprise SaaS
    📨 Apply: https://devjobs.co.il/job-details/4161985284
    💡 NICE Actimize seat with an AI-Quality mandate — direct map onto your
       AI-adoption specialty.

  ↪ Director of Software Engineering — DriveNets  ⭐ 7.0/10
    🤝 Internal: Sefi Shaul-Frieman (sfrieman@drivenets.com) — added by Iris
    📨 Apply: https://drivenets.com/careers/
    ...

  ↪ Skipped this run
    • Watchlist with no openings: Cato, monday.com, JFrog, ...
    • Apply-URL verification failures: <none>
    • Notes / blocked sources: ...
```

Five things make this useful day-to-day:

1. **Dedup** — you never see the same role twice.
2. **Apply-URL verification** — dead links get dropped before you click them.
3. **Warm-intro detection** — if a role's company is in your network sheet, the contact's name and a +0.5 score bonus show up.
4. **Skipped-this-run transparency** — you see what was scanned but excluded, so you trust the "no new positions" days.
5. **Duplicate-fire guard** — if cron double-fires, the second run aborts on its own.

## Install (two paths)

### Path A — interactive setup (recommended)

If you also installed the `job-scanner-setup` skill, just invoke it:

```
/job-scanner-setup
```

It will:
1. Read your uploaded CV (drag-and-drop it into the chat first).
2. Ask 5–7 quick questions (target titles, location, Slack channel, run time, watchlist, network sheet).
3. Write a personalized SKILL.md into `~/.claude/skills/job-scanner/` (or the equivalent on your platform).
4. If you're using Cowork, optionally register the scheduled task for you.

You're done.

### Path B — manual

1. Copy `SKILL.md` to `~/.claude/skills/job-scanner/SKILL.md`.
2. Open it and replace every `<<<PLACEHOLDER>>>` with your value (see reference below).
3. Save.
4. Register it as a scheduled task — see "Scheduling" below.

## Placeholder reference

Every `<<<PLACEHOLDER>>>` in `SKILL.md` is a value you supply. Order matters: the early sections (USER, ROLE TITLES, LOCATION) are read by the agent on every run and shape every decision.

| Placeholder                  | What it is                                    | Example                                                                                                |
| ---------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `<<<USER_NAME>>>`            | Your full name                                | `Alex Cohen`                                                                                           |
| `<<<USER_TITLE>>>`           | Your current role title                       | `Senior Engineering Manager, fintech`                                                                  |
| `<<<USER_BIO>>>`             | Multi-line bio block (CV summary)             | See "Bio block format" below                                                                           |
| `<<<USER_LINKEDIN>>>`        | LinkedIn URL                                  | `linkedin.com/in/alex-cohen/`                                                                          |
| `<<<RUN_TIME>>>`             | When the scan should run (display only)       | `08:00`                                                                                                |
| `<<<SENIORITY_LEVEL>>>`      | Short label for digest framing                | `senior engineering leadership`                                                                        |
| `<<<TARGET_MARKET>>>`        | The market you're scanning                    | `Israeli tech`, `Berlin tech`, `London fintech`                                                        |
| `<<<ROLE_TITLES>>>`          | Multi-line list of titles you target          | See "Role titles format" below                                                                         |
| `<<<PRIMARY_TITLE>>>`        | One canonical title used in search queries    | `Director of Engineering`                                                                              |
| `<<<LOCATION_DESC>>>`        | Multi-line corridor / city / hybrid policy    | See "Location format" below                                                                            |
| `<<<LOCATION_KEYWORD>>>`     | Short keyword for search queries              | `Israel`, `London`, `Berlin`                                                                           |
| `<<<COMPANY_REQUIREMENTS>>>` | Multi-line: headcount floor, preferred/skip   | See "Company requirements format" below                                                                |
| `<<<REGIONAL_JOB_BOARDS>>>`  | Job boards specific to your market            | `comeet.co<br>allJobs.co.il<br>drushim.co.il` (Israel) or whatever fits your region                    |
| `<<<OPTIONAL_SOURCES>>>`     | Extra source descriptions (SecretHunter, etc) | Optional — leave blank or add region-specific feeds                                                    |
| `<<<DNA_FIT_FACTORS>>>`      | What "fit" means for you (used in scoring)    | `B2B SaaS, PLG, Node/TypeScript stack`                                                                 |
| `<<<WATCHLIST>>>`            | Companies whose careers pages get checked     | See "Watchlist format" below                                                                           |
| `<<<NETWORK_SHEET_TITLE>>>`  | Display name of the sheet (if any)            | `Open positions`                                                                                       |
| `<<<NETWORK_SHEET_ID>>>`     | Google Sheet file ID (or blank to skip)       | `1IesF1TciTpodPgUqv96UbFwJwIkuSnbPkIQy6N3ZhFg`                                                         |
| `<<<SKIP_LIST>>>`            | Multi-line list of companies to never report  | See "Skip list format" below                                                                           |
| `<<<SLACK_CHANNEL_ID>>>`     | Slack channel ID (the C... value, NOT a name) | `C06AMNPCKKR`                                                                                          |
| `<<<SLACK_CHANNEL_NAME>>>`   | Channel name (display only)                   | `#my-job-search`                                                                                       |

### Bio block format

Multi-line, written as a bulleted list. Keep it tight — the agent reads this on every run.

```
- Current role: Senior Engineering Manager — Payments, ExampleCo
- Experience: 12+ years — developer → tech lead → EM → SEM
- Tech stack: Java, Kotlin, Spring Boot, AWS, PostgreSQL
- Specialty: payment systems, regulated infrastructure, team scaling
- Education: B.Sc. Computer Science, Technion
- Looking for: Director of Engineering / Head of Engineering at fintech or B2B SaaS
```

### Role titles format

```
- Director of Engineering / Engineering Director
- Head of Engineering / Head of R&D
- VP Engineering / VP R&D
- Group Manager R&D
```

### Location format

```
Israel — corridor between Netanya and Tel Aviv:
Netanya, Herzliya, Ra'anana, Kfar Saba, Petah Tikva,
Bnei Brak, Ramat Gan, Givatayim, Tel Aviv.
Hybrid OK. Remote OK if HQ is in this area.
```

### Company requirements format

```
- 100+ employees minimum
- Prefer: B2B SaaS, PLG, Cloud, AI/ML, data platforms
- Acceptable: any software/tech company
- Skip: hardware-only, semiconductor fabs, defense-only,
  hospitality, retail, non-tech
```

### Watchlist format

Company name + careers URL + your perceived score (used to prioritize the scan order and label the "Skipped this run" report).

```
catonetworks.com/careers      [score: 9.5 — top priority]
monday.com/careers            [score: 9.0 — top priority]
jfrog.com/careers             [score: 8.5 — top priority]
your-target-company.com/jobs  [score: 7.0]
```

### Skip list format

```
- ExampleCo (your current employer)
- AcquiredCo (acquihired by current employer)
- TroubledCo (mass layoffs, stock down >70%)
```

## Network sheet (optional, recommended if you have one)

If you have a Google Sheet of companies where someone you know can warm-intro your CV, set `<<<NETWORK_SHEET_ID>>>` to the file's ID (the long string in the URL after `/d/`).

The expected sheet schema is:

| Company Name | Jobs page URL | Office location | Contact person | Added by | More info |
| ------------ | ------------- | --------------- | -------------- | -------- | --------- |

When the scanner finds a matching role at a sheet company, the digest shows the contact's name + how to reach them, and the role gets a +0.5 score bonus to prioritize warm-intro paths.

If you don't have a network sheet, leave `<<<NETWORK_SHEET_ID>>>` blank — the setup helper will strip the STEP 2.5 section entirely. The scanner still works fine without it.

## Scheduling

The scanner itself is a regular Claude skill — it works ad-hoc if you invoke `/job-scanner` manually. But you want it on a daily cron. That's a Cowork feature, not a Claude Code feature.

### In Cowork

After dropping the personalized SKILL.md into `~/Documents/Claude/Scheduled/job-scanner/`, open Cowork and type:

```
Schedule the job-scanner skill to run every day at 8am.
```

Cowork's built-in `/schedule` skill registers a cron entry. You can verify it by typing "list my scheduled tasks".

### In Claude Code (CLI)

Claude Code doesn't ship with built-in cron. Options:
1. Use your OS scheduler (macOS `launchd`, Linux `cron`, Windows Task Scheduler) to invoke `claude -p "Run the job-scanner skill"` at the desired time.
2. Use Cowork for the scheduling piece even if you use Claude Code for everything else — the two share the same skill format.

## MCP server requirements

The scanner expects these MCPs to be available at runtime:

| MCP                | Used for                                                          | Required? |
| ------------------ | ----------------------------------------------------------------- | --------- |
| Slack              | Posting the digest, reading prior runs for dedup                  | Required  |
| Web search + fetch | Scanning job boards, verifying apply URLs                         | Required  |
| Google Drive       | Reading the network sheet (STEP 2.5)                              | Optional — only if you set `<<<NETWORK_SHEET_ID>>>` |
| Claude in Chrome   | Scanning JS-rendered boards (Wellfound, SecretHunter, etc.) directly when egress-blocked | Optional — falls back to Google site: search |

## Troubleshooting

**"Unable to connect to API (ConnectionRefused)" when opening the chat the next morning.**
The chat got too big. The scanner is supposed to delegate heavy page fetches to subagents (EXECUTION HYGIENE rule 1) so the main chat stays small. If you see this error, the agent broke that rule — re-read the EXECUTION HYGIENE section of SKILL.md and consider running with a fresh chat.

**Cron double-fires and you get two digests seconds apart.**
This happens occasionally on every cron platform. STEP 0 (the duplicate-fire guard) should prevent it — the second run reads the channel, sees today's parent message already exists, and aborts. If it doesn't, check that the parent message timestamp is being captured correctly.

**Dead apply links sneak into the digest.**
STEP 4.5 verifies every URL before posting. If a dead link shows up anyway, the ATS likely uses a "200 + search page" pattern that wasn't matched — add the specific phrasing to the STEP 4.5 ATS list and the scanner will catch it next run.

**Network sheet hits a Google Sheets API quota.**
The setup waits 60s and retries once. If that still fails, the agent falls back to `download_file_content`. If both fail, the run skips STEP 2.5 and notes it in Message 3 — you'll see "Notes / blocked sources" in the digest.

**Too many low-fit roles in the digest.**
Tighten `<<<COMPANY_REQUIREMENTS>>>` (raise the headcount floor, narrow preferred industries) and add the noise sources to `<<<SKIP_LIST>>>`. The scanner respects both on every run.

## Origin

Adapted from the original `looker` scheduled task that runs daily for the repo owner. Battle-tested for several months, with every quirk in the SKILL.md (the duplicate-fire guard, the chat-size hygiene rules, the apply-URL verification step) added in response to a real production failure. The history note inside each section explains the trigger.
