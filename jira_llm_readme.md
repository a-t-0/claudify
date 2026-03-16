# Jira Ticket Management via REST API - LLM Reusable Guide

Guide for managing Jira Cloud boards programmatically via the REST API.
Used successfully on the SOME other project (some.atlassian.net, project key: other).

## Authentication

```bash
# Basic auth: email + API token
# Generate token at https://id.atlassian.com/manage-profile/security/api-tokens
JIRA_AUTH="user@domain.com:YOUR_API_TOKEN"
```

```python
# For Python (urllib):
import base64
auth_string = base64.b64encode(f"{user}:{token}".encode()).decode()
# Header: Authorization: Basic {auth_string}
```

## API Base

```
https://YOUR-INSTANCE.atlassian.net/rest/api/3/
```

## Search Issues

The old `GET /rest/api/3/search` endpoint is **deprecated**. Use the new POST endpoint:

```bash
curl -s -u "$JIRA_AUTH" -X POST -H "Content-Type: application/json" \
  "https://INSTANCE.atlassian.net/rest/api/3/search/jql" \
  -d '{
    "jql": "project=PROJ AND status IN (\"To Do\",\"In Progress\")",
    "fields": ["summary","status","labels","priority","assignee","parent"],
    "maxResults": 100
  }'
```

### Pagination

Uses `nextPageToken` (NOT `startAt`):

```python
payload = {"jql": "project=PROJ", "fields": [...], "maxResults": 100}
if next_token:
    payload["nextPageToken"] = next_token
# Response contains: issues[], isLast, nextPageToken
```

## Create Issue

```bash
curl -s -u "$JIRA_AUTH" -X POST -H "Content-Type: application/json" \
  "https://INSTANCE.atlassian.net/rest/api/3/issue" \
  -d '{
    "fields": {
      "project": {"key": "PROJ"},
      "summary": "Title here",
      "issuetype": {"name": "Task"},
      "description": {
        "type": "doc", "version": 1,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Description text"}]}]
      },
      "labels": ["label1", "label2"],
      "priority": {"id": "2"},
      "assignee": {"accountId": "712020:xxxxx"},
      "parent": {"key": "PROJ-99"},
      "duedate": "2026-04-01"
    }
  }'
# Returns: {"id": "...", "key": "PROJ-133", "self": "..."}
```

### Priority IDs

| ID | Name |
|----|------|
| 1 | Highest |
| 2 | High |
| 3 | Medium |
| 4 | Low |
| 5 | Lowest |

### Description Format

Descriptions use **Atlassian Document Format (ADF)**, not plain text or markdown:

```json
{
  "type": "doc", "version": 1,
  "content": [
    {"type": "paragraph", "content": [{"type": "text", "text": "Your text here"}]}
  ]
}
```

## Update Issue

### Add Labels (additive, won't remove existing)

```bash
curl -s -u "$JIRA_AUTH" -X PUT -H "Content-Type: application/json" \
  "https://INSTANCE.atlassian.net/rest/api/3/issue/PROJ-42" \
  -d '{"update": {"labels": [{"add": "new-label"}, {"add": "another"}]}}'
```

### Remove Labels

```bash
curl -s -u "$JIRA_AUTH" -X PUT -H "Content-Type: application/json" \
  "https://INSTANCE.atlassian.net/rest/api/3/issue/PROJ-42" \
  -d '{"update": {"labels": [{"remove": "old-label"}]}}'
```

### Change Parent / Epic

```bash
curl -s -u "$JIRA_AUTH" -X PUT -H "Content-Type: application/json" \
  "https://INSTANCE.atlassian.net/rest/api/3/issue/PROJ-42" \
  -d '{"fields": {"parent": {"key": "PROJ-99"}}}'
```

### Rename Summary

```bash
curl -s -u "$JIRA_AUTH" -X PUT -H "Content-Type: application/json" \
  "https://INSTANCE.atlassian.net/rest/api/3/issue/PROJ-42" \
  -d '{"fields": {"summary": "New title"}}'
```

### Combined Update (labels + parent in one call)

```bash
curl -s -u "$JIRA_AUTH" -X PUT -H "Content-Type: application/json" \
  "https://INSTANCE.atlassian.net/rest/api/3/issue/PROJ-42" \
  -d '{
    "update": {"labels": [{"add": "label1"}]},
    "fields": {"parent": {"key": "PROJ-99"}}
  }'
# Success = HTTP 204 (no body)
```

## Create Epic

Same as creating an issue, just change the issue type:

```bash
curl -s -u "$JIRA_AUTH" -X POST -H "Content-Type: application/json" \
  "https://INSTANCE.atlassian.net/rest/api/3/issue" \
  -d '{
    "fields": {
      "project": {"key": "PROJ"},
      "summary": "Epic Name",
      "issuetype": {"name": "Epic"},
      "description": {
        "type": "doc", "version": 1,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Epic description"}]}]
      }
    }
  }'
```

## Link Issues

```bash
curl -s -u "$JIRA_AUTH" -X POST -H "Content-Type: application/json" \
  "https://INSTANCE.atlassian.net/rest/api/3/issueLink" \
  -d '{
    "type": {"name": "Relates"},
    "inwardIssue": {"key": "PROJ-133"},
    "outwardIssue": {"key": "PROJ-42"}
  }'
```

## Transition Issue (change status)

```bash
# Step 1: Get available transitions (IDs vary per project/workflow)
curl -s -u "$JIRA_AUTH" \
  "https://INSTANCE.atlassian.net/rest/api/3/issue/PROJ-42/transitions"
# Returns transitions with IDs, e.g. "11"=To Do, "21"=In Progress, "31"=Done

# Step 2: Apply the transition
curl -s -u "$JIRA_AUTH" -X POST -H "Content-Type: application/json" \
  "https://INSTANCE.atlassian.net/rest/api/3/issue/PROJ-42/transitions" \
  -d '{"transition": {"id": "31"}}'
```

## Get Labels

```bash
# Returns all labels across the entire Jira instance (not project-specific)
curl -s -u "$JIRA_AUTH" "https://INSTANCE.atlassian.net/rest/api/3/label"
```

Labels are created implicitly when you first use them on an issue -- no separate create call needed.

## Discover Project Metadata

```bash
# Issue types for a project
curl -s -u "$JIRA_AUTH" "https://INSTANCE.atlassian.net/rest/api/3/project/PROJ"

# Current user (verify auth works)
curl -s -u "$JIRA_AUTH" "https://INSTANCE.atlassian.net/rest/api/3/myself"

# Find assignable users for a project
curl -s -u "$JIRA_AUTH" \
  "https://INSTANCE.atlassian.net/rest/api/3/user/assignable/search?project=PROJ"
```

## Bulk Operations Pattern

When creating or updating many issues, use a loop with rate limiting:

```python
import time

for issue in issues_to_create:
    key = create_issue(...)
    print(f"Created {key}")
    time.sleep(0.3)  # ~300ms between calls to avoid rate limits
```

For bulk label updates via bash:

```bash
for issue in OTHER-62 OTHER-61 OTHER-58; do
  curl -s -w "%{http_code}" -o /dev/null -u "$JIRA_AUTH" -X PUT \
    -H "Content-Type: application/json" \
    "https://INSTANCE.atlassian.net/rest/api/3/issue/$issue" \
    -d '{"update":{"labels":[{"remove":"old-label"}]}}'
  echo " $issue"
done
```

## Full Backup Pattern

Download all issues with pagination for local backup:

```python
import json, urllib.request, base64, os

auth_string = base64.b64encode(f"{user}:{token}".encode()).decode()
BASE_URL = "https://INSTANCE.atlassian.net/rest/api/3/search/jql"
FIELDS = ["summary","status","issuetype","labels","priority","assignee",
          "parent","description","created","updated","duedate",
          "resolution","comment","reporter","creator"]

all_issues = []
next_token = None

while True:
    payload = {"jql": "project=PROJ ORDER BY key ASC", "fields": FIELDS, "maxResults": 100}
    if next_token:
        payload["nextPageToken"] = next_token

    req = urllib.request.Request(BASE_URL, json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Basic {auth_string}")

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())

    all_issues.extend(data.get("issues", []))

    if data.get("isLast", True):
        break
    next_token = data.get("nextPageToken")

with open("backup.json", "w") as f:
    json.dump({"total": len(all_issues), "issues": all_issues}, f, indent=2)
```

## Key Gotchas

1. **Search endpoint changed**: Use `POST /rest/api/3/search/jql`, not the old `GET /rest/api/3/search`
2. **Pagination**: Uses `nextPageToken`, not `startAt`
3. **Descriptions**: Must be ADF (JSON document format), not plain strings or markdown
4. **Labels**: Created on first use, no separate API call needed
5. **PUT returns 204**: No response body on success -- check HTTP status code
6. **Rate limiting**: Add ~300ms delay between bulk operations
7. **Parent = Epic**: In Jira Cloud next-gen projects, the `parent` field assigns an issue to an epic (not a custom `epic_link` field)
8. **Transition IDs**: Vary per project/workflow -- always query available transitions first
9. **Labels are instance-global**: The labels endpoint returns labels from all projects, not just yours
