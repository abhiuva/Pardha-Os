# PARDHA-18 Jira Connector

Pardha can synchronize objective-driven work into Jira Cloud while keeping local audit records for projects, issues, and sync history.

## Configuration

Set these environment variables before starting FastAPI:

```bash
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=person@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=EAT
PARDHA_JIRA_ENABLED=true
```

## API

- `GET /jira/status` reports configuration, counts, and the latest sync.
- `POST /jira/sync` creates or synchronizes an objective into Jira.
- `GET /jira/issues` returns locally stored Jira issues.
- `GET /jira/projects` returns locally stored Jira project configuration.

Example sync request:

```json
{
  "title": "Launch EatOnTime in 3 new schools",
  "description": "Coordinate product, onboarding, and engineering delivery for three new schools.",
  "business_name": "EatOnTime",
  "priority": "high"
}
```

## Mapping

- Objective -> Jira Epic
- Product task -> Jira Story
- Engineering task -> Jira technical Story

The connector stores created Jira keys in `jira_issues` and records each sync in `jira_sync_history`.
