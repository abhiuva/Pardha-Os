# Memory and Connector Audit

## Memory Architecture

Pardha has multiple overlapping memory concepts:

- Generic `Memory` rows with business, agent, content, metadata (`app/memory/engine.py:13-123`).
- Founder, Business, Specialist, Conversation, and Learning memory SQLAlchemy models (`app/db/models.py:1128-1190`).
- Conversation messages, summaries, snapshots, and timeline events.
- Knowledge records used as contextual evidence.
- Operational-learning signals derived from execution outcomes.

## Memory Findings

| Capability | Status | Finding |
|---|---|---|
| Durable storage | Implemented | SQLAlchemy persistence |
| Business filtering | Implemented in common reads | `app/memory/engine.py:76-104` |
| Semantic retrieval | Missing | Search is lowercase substring matching (`:98-123`) |
| Embeddings/vector store | Not operational | Fields may exist, but no active embedding pipeline was found |
| Consolidated memory policy | Missing | Several memory models and stores overlap |
| Retention/deletion policy | Missing | No tenant-level retention/deletion policy defined yet |
| Provenance/evidence | Partial | Knowledge has source metadata; generic memory is weaker |
| Learning | Rules only | Signals are stored; no model adaptation occurs |

Knowledge upload is not training. Files are validated, text extracted, hashed for duplicate prevention, and stored for later context. Search and prompt context may use that text, but no weights are updated in real time.

## Connector Matrix

| Connector | Read | Write | Auth/health truth | UI | Status |
|---|---|---|---|---|---|
| Jira | Real REST client | Real create/update | Status incorrectly reports connected in some missing-config cases (`app/jira/service.py:47-72`) | Yes | Partial/risky |
| HubSpot | Real client foundation | Gated direct sync | Configuration + mode; MCP is draft-first | Yes | Partial |
| Gmail | No real provider client | Mock/draft | Configuration/status only | Yes | Stub/mock |
| Outlook | No real provider client | Mock/draft | Configuration/status only | Yes | Stub/mock |
| WhatsApp | No live implementation | Local mock “sent” | Live path raises not implemented | Yes | Mock |
| Google Calendar | Availability/status foundation | No proven live booking client | Status/config | Yes | Stub |
| GitHub | Status/config surface | No proven live tool loop | Status/config | Yes | Stub |
| VS Code | Local status concept | No controlled editor execution | Status | Yes | Stub |
| Meta/Instagram | Read-first/mock ingestion | Draft approval records | MCP write tools return approval requirement | Yes | Foundation |
| Ollama | Real local HTTP | Model management endpoints | Real local checks | Yes | Implemented optional provider |

## Context Isolation Test

An isolated benchmark inserted unique markers into DP360 and EatOnTime. A conversation scoped to EatOnTime did not include the DP360 marker. This supports business-filtering behavior for that path only; it is not proof of adversarial tenant isolation, which is verified separately under PE0OM-56.

## Key Recommendations

- Consolidate memory into episodic conversation memory, durable business facts, knowledge documents, and execution/audit history.
- Add provenance, confidence, sensitivity, retention, and supersession fields.
- Use hybrid retrieval only after access control is enforced at query time.
- Define connector states as `unconfigured`, `configured`, `auth_failed`, `connected`, `degraded`, and `mock`; never collapse configuration into connection.
- Route all connector writes through one approval/policy executor.

