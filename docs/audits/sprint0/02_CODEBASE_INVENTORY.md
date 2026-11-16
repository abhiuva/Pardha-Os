# Codebase Inventory

## Repository State

| Item | Finding |
|---|---|
| Parent repository | original local parent checkout, branch `feature/PE0OM-19-reasoning-gateway`, commit `12bd783` |
| Application repository | original local `pardha-core` checkout, branch `feature/PE0OM-ceo-agent-mvp`, commit `422857f` (now published under `pardha-core/` in this repo) |
| Parent linkage | Broken gitlink: `pardha-core` has no `.gitmodules` mapping |
| Recovery work | Separate draft monorepo PR #1 exists on `chore/publish-pardha-monorepo`; not merged/deployed |
| Application worktree | Existing uncommitted CEO-agent files; preserved unchanged |

The broken gitlink is a source-distribution risk: GitHub cannot reconstruct the full application from the parent repository alone.

## Backend Inventory

| Area | Location | Status |
|---|---|---|
| Application composition | `app/main.py` | Implemented; startup performs DB/admin/demo/capability/scheduler work |
| Data layer | `app/db/`, `migrations/` | 34 migration files; PostgreSQL default; model/schema parity not proven here |
| Business context | `app/business/` | Implemented; per-session context scoping planned (PE0OM-56) |
| Knowledge | `app/knowledge/` | Upload/extract/dedupe/search/delete implemented |
| Core agents | `app/agents/` | CEO/PM/CTO deterministic services and scheduler |
| Conversation | `app/conversations/` | Persistent, structured, rule-routed; partial streaming/model use |
| Planning | `app/planning/` | Persistent graph/approval model; execution semantics incomplete |
| Capabilities | `app/capabilities/` | Registry, scoring, adapters, execution history |
| Runtime | `app/runtime/` | Queue/execution/retry/rollback records; adapters remain limited |
| Sales/Marketing | `app/sales/`, `app/marketing/` | Functional deterministic workspaces with mock/read-first integrations |
| Connectors | `app/jira/`, `app/hubspot/`, `app/communications/`, `app/whatsapp/`, `app/mcp/` | Mixed real, mock, and draft-only implementations |
| Enterprise | `app/enterprise/` | Broad models/status surfaces; enforcement depth varies |
| Auth | `app/auth/` | Login/session implemented; API-wide enforcement in progress (PE0OM-56) |
| Software factory | `app/software_factory/` | Artifact planning, not autonomous code production/deployment |

## Frontend Inventory

- React 19 + Vite 8 (`dashboard/package.json`).
- No client routing library; page selection is internal state in `dashboard/src/App.jsx`.
- Founder, Knowledge, Planning, Enterprise, Operations, Sales, Marketing, Product Factory, integrations, and diagnostics views are present.
- Knowledge upload/delete, approvals, goals, conversation, and connector actions are wired to APIs.
- The dominant implementation is a single `App.jsx` file exceeding 3,000 lines, making isolation and testability poor.
- No frontend test script is declared; scripts are only `dev`, `build`, and `preview`.

## Test and Delivery Inventory

- 43 Python test files discovered; 159 tests executed in the audit.
- No CI workflow, Dockerfile, Compose, or Kubernetes manifest was found in the audited tree.
- No automated browser/UI test suite was found.
- README documents selected unittest commands, not a single canonical quality gate.

## Startup Side Effects

`app/main.py:145-156` initializes tables, creates an admin, may seed demo data in development, registers capabilities and enterprise defaults, starts provider monitoring, knowledge watcher, and scheduler. Import/startup therefore changes database state and starts background activity; production startup should separate migrations and explicit seed operations.

## Configuration Observations

- PostgreSQL default: `postgresql+psycopg2:///pardha_core` (`app/db/__init__.py:6-9`).
- Ollama is disabled by default, model `llama3.2:3b`, optional `qwen3:8b`, concurrency 1 (`app/settings.py:45-71`).
- Connector mode defaults to `mock` (`app/settings.py:69`).
- Development mode is the default (`app/settings.py:46`).
- CORS is fixed to `http://localhost:5174` (`app/main.py:72-78`), creating likely local mismatch with Vite’s usual 5173.

