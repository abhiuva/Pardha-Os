# Pardha v2.0 Sprint 3: Autonomous Planning Engine and Goal Intelligence

## Mission

Sprint 3 adds first-class goals, executable plans, graph-based orchestration, HITL approvals, plan execution tracking, KPIs, and daily executive planning.

This sprint does not add voice, advanced UI redesign, or new business capabilities.

## Architecture

```text
Founder
  |
Conversation Engine
  |
Conversation Memory
  |
Business Context Resolver
  |
Planning Engine
  |
Execution Graph Builder
  |
Capability Negotiation
  |
Execution Plan
  |
Human In The Loop
  |
Execution Manager
  |
Verification Engine
  |
Conversation Response
```

## Database

Tables:

- `planning_goals`
- `execution_plans`
- `execution_plan_nodes`
- `plan_approvals`
- `plan_executions`
- `goal_kpis`
- `planning_timeline_events`

Migration:

- `migrations/020_create_planning_engine.sql`

## APIs

- `POST /planning/plan`
- `GET /planning/goals`
- `GET /planning/plans`
- `GET /planning/plans/{plan_id}`
- `POST /planning/plans/{plan_id}/approve`
- `POST /planning/plans/{plan_id}/reject`
- `POST /planning/plans/{plan_id}/execute`
- `GET /planning/approvals`
- `GET /planning/daily`
- `GET /planning/goals/{goal_id}/timeline`
- `GET /planning/goals/{goal_id}/kpis`

## Execution Graph

Each plan includes:

- Goal
- Objectives/milestones
- Capability nodes
- Verification nodes
- Dependencies
- Parallel groups
- Critical path
- Estimated runtime
- Risk classification
- Approval requirements

## HITL Rules

Low risk:

- Search
- Read
- Analyze
- Summarize

Medium risk:

- Create goals
- Create tasks
- Create Jira/document/sprint work
- Customer acquisition plans

High risk:

- Send email
- Launch campaigns
- Modify production data
- Deploy software
- Merge code
- Delete knowledge

Medium and high risk plans enter `waiting_approval` unless explicitly pre-approved.

## Conversation Integration

Action-oriented conversation prompts now create executable plans instead of text-only responses.

Example:

```text
Founder: We need 5 eCommerce pilot customers.

Response:
Goal Created
Execution Plan Generated
Marketing Strategy Ready
Sales Plan Ready
Timeline Ready
Approval Required
```

Read-only requests such as health checks, status checks, summaries, and reviews still use the Conversation Engine's kernel execution path.

## UI

Dashboard tab added:

- `Planning`

The tab shows:

- Planning goals
- Execution plans
- Pending approvals
- Latest execution graph
- Plan progress
- Approve / execute actions

## Validation

Focused tests:

```bash
rm -f test_planning_engine.db
env PARDHA_ADMIN_EMAIL=founder@pardha.local PARDHA_ADMIN_PASSWORD='test-password' ./venv/bin/python -m unittest tests.test_planning_engine
```

Coverage:

- Goals as first-class objects
- Plan generation
- Execution graph creation
- Capability negotiation
- HITL approval creation
- Approval and execution flow
- KPI tracking
- Timeline creation
- Daily executive planning
- Conversation-to-plan integration

## Known Limitations

- Execution graph is deterministic and uses existing registered capabilities only.
- Plan execution runs safe/local capability adapters; high-risk external actions remain approval-gated and not provider-live.
- Planner does not yet perform advanced dependency optimization.
- KPI progress is initialized and trackable; continuous metric ingestion is a later milestone.
- Approval modify/comment is represented by decision comments; full plan editing is future work.
