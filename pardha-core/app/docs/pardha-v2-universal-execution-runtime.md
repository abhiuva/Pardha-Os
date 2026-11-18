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

Execution safety (PE0OM-75):

- An execution runs only after an atomic claim (`queued`/`waiting` → `running`). Concurrent direct runs,
  queue processors and retries execute each node at most once; a losing queue item is marked `superseded`.
- Queue items are claimed atomically (`queued` → `processing`) before processing.
- `POST /runtime/executions/{execution_id}/retry` only **queues** one retry (status `queued`); it does not also run
  immediately. Repeated retries while one is pending are idempotent. A `completed` or otherwise non-retryable
  execution returns `409`.
- Re-running an execution skips nodes that already completed.
- `POST /runtime/executions/{execution_id}/rollback` atomically cancels an execution that is **not** running.
  Rolling back a `running` execution returns `409` (cancelling underneath an active worker would let a retry
  start a second concurrent attempt). Rolling back an already-cancelled execution is a no-op.
- Attempt-generation fencing: `retries` is the attempt generation. Every ownership change increments it; a
  worker claims one generation and can persist results (node states, tool invocations, notifications, plan
  status, failure records) only while the execution is still `running` at that generation. A stale worker's
  results are discarded.

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
- **High-risk node approval is not implemented (PE0OM-78).** Approving a plan does not approve its
  approval-required (high-risk) nodes, and no stored node status unlocks them. Such nodes always remain
  `waiting`, so plans containing them cannot complete. This is deliberate fail-closed behaviour, not a bypass;
  verified, payload-bound node approval arrives with PE0OM-78.
- **No lease expiry or automatic recovery yet (deferred to PE0OM-78).** If a worker process dies without
  raising (killed, host crash), its execution stays `running` and its queue item `processing`; rollback
  returns `409` and retry is a no-op for it. Automatic recovery was deliberately not added in PE0OM-75: a
  time-based takeover cannot tell a slow worker from a dead one, and capability calls that already ran
  cannot be fenced after the fact, so it could duplicate side effects. **Dependency:** no unattended or
  background queue worker (scheduler, cron, the PE0OM-82 coordinator or similar) may process the runtime
  queue until PE0OM-78 adds leases with heartbeats/expiry, fenced takeover (generation increment) and
  idempotent capability execution. Until then queue processing stays explicit and operator-driven.
- **Exactly-once is per runtime execution, not per plan node (deferred to PE0OM-78).** The claim and
  fencing above stop one execution from running twice. They do not stop **different** entry points from
  running the same plan's nodes: `POST /planning/plans/{plan_id}/execute` re-runs every eligible node on each
  call (repeated or concurrent calls repeat capability calls), and two separate runtime executions of the
  same plan can run its nodes concurrently. In PE0OM-75 this can only repeat **verified read-only**
  capabilities (the capability allowlist) and can never reach an external write (kill switch plus verified
  authorization). **Dependency:** PE0OM-78 must add plan-node-level exactly-once claims across the planning
  and runtime paths **before** any write-capable adapter is allowlisted.
