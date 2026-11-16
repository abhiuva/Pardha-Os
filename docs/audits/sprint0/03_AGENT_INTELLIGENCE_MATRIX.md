# Agent Intelligence Matrix

## Classification

| Agent/Department | Runtime implementation | Model use | Context | Tools/actions | Collaboration | Status |
|---|---|---|---|---|---|---|
| CEO | Aggregates agents, events, memories and priorities in `app/agents/ceo.py:142+` | None in normal brief | Business filtered | Read/brief | Receives scripted workflow events | Deterministic service |
| PM | Backlog/roadmap aggregation in `app/agents/pm.py:264-316` | None | Business filtered | Jira helper methods can write | Calls CEO/CTO functions directly | Deterministic service with risky helpers |
| CTO | Project/event/memory categorization in `app/agents/cto.py:326-414` | None | Business filtered | Jira helper methods can write | Called by PM/workflow | Deterministic service with risky helpers |
| Sales | CRM/domain service and templates in `app/sales/` | None in core flows | Business filtered | Local CRM, drafts, booking | Exposed as capabilities | Implemented department service |
| Marketing | Campaign/content/analytics service in `app/marketing/` | None in core flows | Business filtered | Local records; Meta draft gate | Exposed as capabilities | Implemented department service |
| Operations | Runtime queues, notifications, automation in `app/runtime/` | None | Business filtered | Executes registered adapters | Reads planning approvals | Partial execution service |
| QA | Labels, priorities, and hardcoded factory plans | None | Indirect | No autonomous test runner agent | No independent mailbox | Missing as agent |
| Knowledge | Upload/extraction/search service | None | Business filtered | Store/search/delete | Emits events to executives | Implemented retrieval service |
| Founder/Chief of Staff | Conversation orchestration in `app/conversations/service.py:176-331` | Conditional shared composer | Business snapshot | Plans/capabilities | Central caller | Partial orchestrator |
| Local CEO MVP | `app/ceo_agent/` | Shared gateway | Snapshot | Approval records | None durable | Uncommitted prototype |

## Intelligence Findings

### Per-agent model selection

Not implemented. Agents do not declare or negotiate an independent model. The conversation router chooses labels such as `deterministic` or `ollama_qwen` by keyword (`app/conversations/executive_router.py:52-93`), and response composition uses one shared gateway (`app/conversations/composer.py:159-225`).

### Prompting and reasoning

- One Chief-of-Staff composer prompt exists (`app/conversations/composer.py:170-180`).
- CEO/PM/CTO briefs are templates and rules, not LLM reasoning.
- “Learning” records operational signals derived from outcomes and keywords; it does not update model weights (`app/conversations/learning.py:11-103`).
- Agent reasoning endpoints share the same provider gateway; they are not durable independent cognitive loops.

### Collaboration

The objective workflow is a deterministic sequence: CEO event -> PM stage -> CTO stage -> completion event (`app/collaboration/service.py:220-285`). Epics and tasks are generated from fixed templates (`:68-217`). The event bus inserts rows into PostgreSQL (`app/events/bus.py:52-102`) but is not an asynchronous broker or subscriber system.

### Delegation

Delegation is represented by planned capabilities and persisted nodes. The controlled request “Delegate a pilot customer campaign to marketing and sales” produced one waiting-approval plan containing CEO, Marketing, Sales, and Tasks capabilities. This is useful orchestration metadata, but no independent agents negotiated ownership, exchanged messages, or verified each other’s outputs.

## Autonomy Level

| Level | Meaning | Current result |
|---|---|---|
| 0 | Static UI/status | Some enterprise and connector surfaces |
| 1 | Deterministic tool/service | CEO, PM, CTO, Sales, Marketing, Knowledge |
| 2 | Contextual orchestration with persistence | Conversation and planning, partially |
| 3 | Model-led planning with guarded tools | Not reliably implemented |
| 4 | Multi-agent delegation and verification | Not implemented |

**Current overall autonomy: 1.8/4.**

## Required v1 Change

Keep departments as tool domains. Add one accountable orchestrator that uses structured model output for intent/plan proposals, then passes every action through policy, approval, idempotency, execution, and verification services. Introduce specialist model loops only where they demonstrably outperform deterministic tools.

