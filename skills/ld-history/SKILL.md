---
name: ld-history
description: >
  Query LaunchDarkly flag change history, audit logs, and last-modified dates
  using the REST API. Supplements the LD MCP which lacks audit/history support.
when_to_use: >
  "LD change history", "flag audit log", "when was flag changed",
  "who modified flag", "LD last modified", "flag changelog",
  "LD audit", "flag history"
allowed-tools: Bash, Read, Grep, Glob, mcp__launchdarkly__get-flag, mcp__launchdarkly__get-flag-health, mcp__launchdarkly__get-flag-status-across-envs, mcp__launchdarkly__list-flags, mcp__launchdarkly__list-experiments
---

# LaunchDarkly History & Audit Skill

## Overview

The LaunchDarkly MCP integration provides flag targeting, health, and config
data but does NOT support:
- `lastModified` timestamps
- Audit log / change history (who changed what and when)

This skill fills that gap by combining:
- **LD MCP tools** for targeting config, health, lifecycle state
- **LD REST API** for `lastModified`, audit logs, and change history

## API Configuration

The LD API token is stored in the auto-memory file at:
`~/.claude/projects/-Users-gal-orr-git/memory/MEMORY.md`

Read it at the start of every invocation:
```
API_TOKEN="api-***"
```

Base URL: `https://app.launchdarkly.com/api/v2`

All curl calls use:
```bash
curl -s -H "Authorization: $API_TOKEN" "$BASE_URL/..."
```

## Capabilities

### From LD REST API (this skill's primary value)

| Capability | Endpoint |
|---|---|
| `lastModified` per flag per env | `GET /api/v2/flags/{project}/{flag}?env={env}` |
| Full audit log (who/what/when) | `GET /api/v2/auditlog?q={flagKey}&limit=50` |
| Audit log filtered by date | Add `&after={epoch_ms}&before={epoch_ms}` |

### From LD MCP (use alongside)

| Capability | MCP Tool |
|---|---|
| Flag targeting config | `mcp__launchdarkly__get-flag` |
| Lifecycle state + last evaluated | `mcp__launchdarkly__get-flag-health` |
| Cross-environment status | `mcp__launchdarkly__get-flag-status-across-envs` |
| Search/list flags | `mcp__launchdarkly__list-flags` |
| List experiments | `mcp__launchdarkly__list-experiments` |

## API Recipes

### 1. Get `lastModified` for a flag in an environment

```bash
curl -s -H "Authorization: $API_TOKEN" \
  "https://app.launchdarkly.com/api/v2/flags/{PROJECT}/{FLAG_KEY}?env={ENV}" \
  > /tmp/ld_flag.json

python3 << 'PYEOF'
import json, datetime
with open("/tmp/ld_flag.json") as f:
    data = json.load(f)
env = data.get("environments", {}).get("{ENV}", {})
created = datetime.datetime.fromtimestamp(
    data.get("creationDate", 0)/1000, tz=datetime.timezone.utc
).strftime("%Y-%m-%d %H:%M UTC")
lm = env.get("lastModified", 0)
last_mod = datetime.datetime.fromtimestamp(
    lm/1000 if lm > 1600000000000 else lm,
    tz=datetime.timezone.utc
).strftime("%Y-%m-%d %H:%M UTC") if lm else "N/A"
print(f"Flag: {data.get('key')}")
print(f"Created: {created}")
print(f"Last Modified ({'{ENV}'}): {last_mod}")
print(f"Version: v{env.get('version', '?')}")
print(f"ON: {env.get('on', False)}")
PYEOF
```

### 2. Get `lastModified` for multiple flags (batch)

```bash
API_TOKEN="api-***"
PROJECT="test-project"
ENV="production"

for flag in "flag-key-1" "flag-key-2" "flag-key-3"; do
  curl -s -H "Authorization: $API_TOKEN" \
    "https://app.launchdarkly.com/api/v2/flags/${PROJECT}/${flag}?env=${ENV}" \
    > "/tmp/ld_flag_${flag}.json"
done

python3 << 'PYEOF'
import json, datetime, glob
for path in sorted(glob.glob("/tmp/ld_flag_*.json")):
    with open(path) as f:
        data = json.load(f)
    env = data.get("environments", {}).get("production", {})
    created = datetime.datetime.fromtimestamp(
        data.get("creationDate", 0)/1000, tz=datetime.timezone.utc
    ).strftime("%Y-%m-%d %H:%M UTC")
    lm = env.get("lastModified", 0)
    if lm > 1600000000000:
        last_mod = datetime.datetime.fromtimestamp(lm/1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    elif lm > 1600000000:
        last_mod = datetime.datetime.fromtimestamp(lm, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    else:
        last_mod = "N/A"
    print(f"{data.get('key'):50s} | Created: {created} | Last Modified: {last_mod} | v{env.get('version','?')} | ON={env.get('on')}")
PYEOF
```

### 3. Get full audit log for a flag

```bash
curl -s -H "Authorization: $API_TOKEN" \
  "https://app.launchdarkly.com/api/v2/auditlog?q={FLAG_KEY}&limit=50" \
  > /tmp/ld_audit.json

python3 << 'PYEOF'
import json, datetime
with open("/tmp/ld_audit.json") as f:
    data = json.load(f)
print(f"Total entries: {len(data.get('items', []))}\n")
for item in data.get("items", []):
    dt = datetime.datetime.fromtimestamp(
        item["date"]/1000, tz=datetime.timezone.utc
    ).strftime("%Y-%m-%d %H:%M UTC")
    who = item.get("member", {}).get("email", "system/api")
    verb = item.get("titleVerb", "")
    desc = item.get("description", "").replace("\n", " ").strip()[:200]
    env_name = item.get("parent", {}).get("name", "?")
    print(f"{dt} | {env_name:12s} | {who:35s} | {verb}")
    if desc:
        print(f"  {desc}")
    print()
PYEOF
```

### 4. Get audit log filtered by date range

```bash
# after/before are epoch milliseconds
AFTER=$(python3 -c "import datetime; print(int(datetime.datetime(2025,1,1,tzinfo=datetime.timezone.utc).timestamp()*1000))")
BEFORE=$(python3 -c "import datetime; print(int(datetime.datetime(2025,12,31,tzinfo=datetime.timezone.utc).timestamp()*1000))")

curl -s -H "Authorization: $API_TOKEN" \
  "https://app.launchdarkly.com/api/v2/auditlog?q={FLAG_KEY}&limit=50&after=${AFTER}&before=${BEFORE}" \
  > /tmp/ld_audit_filtered.json
```

### 5. Get flag details not available in MCP

The REST API returns fields the MCP strips out:

```bash
curl -s -H "Authorization: $API_TOKEN" \
  "https://app.launchdarkly.com/api/v2/flags/{PROJECT}/{FLAG_KEY}?env={ENV}" \
  > /tmp/ld_flag_full.json

python3 << 'PYEOF'
import json, datetime
with open("/tmp/ld_flag_full.json") as f:
    data = json.load(f)
env = data.get("environments", {}).get("{ENV}", {})

# Fields available from REST but NOT from MCP:
print("lastModified:", env.get("lastModified"))
print("_environmentName:", env.get("_environmentName"))
print("_summary:", json.dumps(env.get("_summary", {}), indent=2))
print("_site:", env.get("_site", {}).get("href"))
print("archived:", data.get("archived", False))
print("archivedDate:", data.get("archivedDate"))
print("_maintainer:", data.get("_maintainer", {}).get("email"))
print("goalIds:", data.get("goalIds", []))
print("experiments:", data.get("experiments", {}))
PYEOF
```

## Combined Workflow: Full Flag Report

When asked for a complete flag report, run these steps:

1. **MCP: Get flag config**
   - Call `mcp__launchdarkly__get-flag` for targeting rules, variations, cohorts

2. **MCP: Get flag health**
   - Call `mcp__launchdarkly__get-flag-health` for lifecycle state, last evaluated, age

3. **MCP: Get cross-env status**
   - Call `mcp__launchdarkly__get-flag-status-across-envs` for all environments

4. **REST API: Get lastModified**
   - Use Recipe #1 or #2 above

5. **REST API: Get audit log**
   - Use Recipe #3 above
   - Filter by date range with Recipe #4 if needed

6. **Present results** in this format:

```markdown
## Flag: {flag-key}
> {description}

| Field | Value |
|---|---|
| Created | {date} |
| Last Modified (prod) | {date} |
| Lifecycle State | {state} |
| Last Evaluated | {date} |
| Version | v{n} |
| Status | ON/OFF |
| Maintainer | {name} ({email}) |
| Targeting | {summary} |

### Change History (Production)

| Date | Who | Action | Description |
|---|---|---|---|
| {date} | {email} | {verb} | {desc} |
```

## Known LD MCP Limitations (use REST API instead)

- No `lastModified` timestamp
- No audit log / change history
- No `_summary` field (variation distribution counts)
- No `_maintainer` details (only maintainerId)
- No archived flag metadata
- No experiment results data
- No approval request history details
