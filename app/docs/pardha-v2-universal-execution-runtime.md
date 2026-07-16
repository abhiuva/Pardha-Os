# Pardha v2.0 Sprint 4: Universal Tool Execution Engine and Department Orchestration

## Mission

Sprint 4 adds the operational runtime that executes business work through one universal engine. It builds on:

- Capability Registry
- Conversation Engine
- Planning Engine
- HITL approvals

This sprint does not add voice, new AI reasoning, or connector-specific UI logic.

## Architecture

```text
Founder
  |
Conversation
  |
Planner
  |
Execution Graph
  |
Universal Execution Engine
  |
Department Orchestrator
  |
Capabilities / Tools
  |
Verification
  |
Notifications + Timeline + Learning Evidence
```

## Database

Tables:

- `runtime_executions`
- `department_runtimes`
- `runtime_queue_items`
- `tool_runtime_invocations`
- `runtime_notifications`
- `automation_rules`
- `business_timeline_events`

Migration:

- `migrations/021_create_universal_runtime.sql`

## APIs

- `POST /runtime/executions`
- `GET /runtime/executions`
- `POST /runtime/executions/{execution_id}/run`
- `POST /runtime/executions/{execution_id}/retry`
- `POST /runtime/executions/{execution_id}/rollback`
- `POST /runtime/queue`
- `GET /runtime/queue`
- `POST /runtime/queue/process`
- `GET /runtime/departments`
- `GET /runtime/notifications`
- `POST /runtime/notifications/{notification_id}/read`
- `POST /runtime/notifications/{notification_id}/archive`
- `POST /runtime/automation/rules`
- `GET /runtime/automation/rules`
- `GET /runtime/timeline`
- `GET /runtime/dashboard`

## Departments

Department runtimes are initialized per business:

- CEO
- CTO
- PM
- Marketing
- Sales
- QA
- Operations
- Customer Success
- Engineering

Each department exposes:

- Objectives
- Capabilities
- Current work
- Queue
- KPIs
- Health
- Owner
- Current load
- Dependencies

## Runtime Contract

Every runtime execution tracks:

- Execution ID
- Business
- Goal
- Plan
- Execution graph
- Current stage
- Current capability
- Logs
- Retries
- Progress
- Duration
- Dependencies
- Rollback strategy
- Status

Statuses:

- queued
- running
- waiting
- paused
- completed
- failed
- cancelled

## Tool Runtime

Tools execute through the same runtime contract:

- Jira
- Gmail / Outlook
- WhatsApp
- Calendar
- VS Code / Projects
- Git / GitHub-ready placeholders
- Ollama-ready manual reasoning surfaces
- Future tools

The UI reads the universal runtime state instead of connector-specific execution logic.

## Queue

Queue items support:

- Priority
- Dependencies
- Retries
- Timeout metadata
- Scheduled metadata
- Recurring flag
- Delayed execution metadata
- Cancellation/recovery through execution status

## Notifications

Central notifications support:

- Priority
- Category
- Business
- Read
- Unread
- Archive

Examples:

- Execution queued
- Execution completed
- Execution failed
- Retry queued
- Rollback completed
- Automation fired

## Automation

Automation rules support:

```text
When trigger_event matches runtime event
Then action executes
```

Current action:

- `notify_founder`

Examples:

- Execution Completed -> Notify Founder
- Execution Failed -> Notify Founder

## Dashboard

Dashboard tab added:

- `Runtime`

It shows:

- Departments
- Executions
- Queue
- Notifications
- Business timeline
- Runtime observability
- Queue latest plan
- Process queue
- Rollback execution

## Validation

Focused tests:

```bash
rm -f test_runtime_engine.db
env PARDHA_ADMIN_EMAIL=founder@pardha.local PARDHA_ADMIN_PASSWORD='test-password' ./venv/bin/python -m unittest tests.test_runtime_engine
```

Coverage:

- Runtime execution creation
- Queue processing
- Tool invocation through one runtime
- Department runtime initialization
- Notifications
- Read/archive notification state
- Automation rule firing
- Business timeline
- Rollback
- Multi-business isolation

## Known Limitations

- Runtime is deterministic and local-first.
- Live external side effects remain bounded by existing connector readiness and provider credentials.
- Queue processing is explicit API-driven in this sprint, not a background worker.
- Git/GitHub/deployment runtime categories are represented by the universal contract, but live provider integrations are not added in this sprint.
- Rollback is currently state-based for safe local execution, not provider-specific undo.
