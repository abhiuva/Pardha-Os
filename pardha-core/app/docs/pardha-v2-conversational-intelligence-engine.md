# Pardha v2.0 Sprint 2: Conversational Intelligence Engine

## Mission

Sprint 2 adds the conversational layer for Pardha's AI Chief of Staff experience. It depends on the v2 Intelligence Kernel and Capability Registry.

This sprint does not implement voice or planner logic.

## Architecture

```text
Founder
  |
Conversation UI
  |
Conversation Engine
  |
Conversation Memory
  |
Context Resolver
  |
Intelligence Kernel
  |
Capability Registry
  |
Execution Adapter
  |
Structured Response
```

The Conversation Engine does not call CEO, PM, CTO, Sales, Marketing, Knowledge, Jira, or other capability services directly. It calls the Intelligence Kernel through `search_capabilities` and `execute_capability`.

## Database Changes

Tables:

- `conversation_sessions`
- `conversation_messages`
- `conversation_timeline_events`

Migration:

- `migrations/019_create_conversation_engine.sql`

## Conversation APIs

- `POST /conversations`
- `GET /conversations`
- `GET /conversations/{conversation_id}`
- `PATCH /conversations/{conversation_id}`
- `POST /conversations/{conversation_id}/restore`
- `GET /conversations/{conversation_id}/export`
- `POST /conversations/messages`
- `POST /conversations/{conversation_id}/messages`
- `POST /conversations/stream`
- `POST /conversations/{conversation_id}/stream`

## Conversation Memory

Each message stores a structured context snapshot containing:

- Business context
- Candidate businesses
- Current objectives
- Current tasks
- Recent executions
- Founder goals
- Knowledge search results
- Diagnostics / integration context
- Context source capability IDs

Context is retrieved through kernel capabilities:

- `business.context`
- `objectives.catalog`
- `tasks.catalog`
- `executions.catalog`
- `founder_goals.catalog`
- `knowledge.search`
- `diagnostics.system_health`

## Conversation Types

The engine classifies conversation type using deterministic routing:

- General Conversation
- Business Strategy
- Marketing
- Sales
- Engineering
- Architecture
- Product Management
- Research
- Troubleshooting
- Diagnostics
- Reverse Engineering
- Executive Review
- Knowledge Search
- Sprint Planning
- Code Review
- Project Review
- General Help

## Response Structure

Every assistant response includes:

- Executive Summary
- Reasoning
- Capabilities Used
- Evidence
- Confidence
- Next Recommended Actions
- Execution ID, status, and duration when a capability executes
- Verification summary

## Timeline

Each turn writes timeline events:

```text
Question
  -> Intent
  -> Capability Selection
  -> Execution
  -> Verification
  -> Result
```

## Streaming

Streaming endpoints emit newline-delimited JSON phases:

- `thinking`
- `planning`
- `executing`
- `verifying`
- `completed`

## UI

The `Ask Pardha` dashboard tab now uses `/conversations/*` APIs. It shows:

- Conversation messages
- Conversation history
- Capability timeline
- Suggested actions
- Prompt shortcuts

Voice controls are intentionally not included in Sprint 2.

## Validation

Focused tests:

```bash
rm -f test_conversational_intelligence.db
env PARDHA_ADMIN_EMAIL=founder@pardha.local PARDHA_ADMIN_PASSWORD='test-password' ./venv/bin/python -m unittest tests.test_conversational_intelligence
```

Coverage:

- Persistent conversation creation
- Kernel-only capability execution
- Structured context snapshot
- Timeline persistence
- Conversation search
- Pin/archive/restore
- Export
- Streaming phases
- Business clarification behavior

## Known Limitations

- Responses are deterministic structured executive responses, not free-form LLM prose.
- Streaming currently emits lifecycle phase chunks, not token-by-token model output.
- Clarification is supported for missing business context, but multi-turn clarification selection is still basic.
- The old `/chief/*` API remains for backward compatibility; the Sprint 2 UI uses `/conversations/*`.
- Voice and planner functionality remain future milestones.
