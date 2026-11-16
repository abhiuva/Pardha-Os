# Pardha 4.0 Database Gap Report

## Summary

PostgreSQL was audited before changes. Existing structures were reused where practical. Missing structures were added through one additive migration: [026_pardha_4_database_foundation.sql](/Users/abhishekkola/pardha/pardha-core/migrations/026_pardha_4_database_foundation.sql).

## Existing Before v4

| Requirement Area | Existing Structure | Status |
|---|---|---|
| Conversation sessions | `conversation_sessions` | Reused; missing v4 aliases/metadata columns before migration |
| Conversation messages | `conversation_messages` | Reused; missing planner/specialist/model/tool/tokens/latency columns before migration |
| Conversation timeline | `conversation_timeline_events` | Existing and retained |
| Agent registry | `agents` | Existing but insufficient for specialist scopes/prompts |
| Capability registry | `capabilities`, `capability_executions` | Existing and retained |
| Runtime tools | `tool_runtime_invocations`, `runtime_executions`, `runtime_queue_items` | Existing and retained |
| Learning | `founder_operational_learning` | Existing and retained |
| Business memory source | `knowledge`, `memories` | Existing and retained |
| Multi-tenancy | `tenants`, `tenant_users`, tenant FKs | Existing and retained |

## Missing Before v4

| Required Entity | Action Taken |
|---|---|
| `conversation_context` | Created |
| `conversation_intents` | Created and seeded |
| `specialists` | Created and seeded |
| `reasoning_models` | Created and seeded with Ollama Qwen, Ollama Llama, and future providers |
| `mcp_servers` | Created and seeded with local MCP runtime placeholder |
| `capability_routes` | Created and seeded for key initial routes |
| `founder_memory` | Created |
| `business_memory` | Created |
| `specialist_memory` | Created |
| `conversation_memory` | Created |
| `learning_memory` | Created |
| `learning_events` | Created |
| `voice_sessions` | Created |
| `execution_trace` | Created |

## Existing Tables Extended

| Table | Columns Added |
|---|---|
| `conversation_sessions` | `id`, `founder_id`, `started_at`, `ended_at`, `status`, `voice_enabled`, `current_context` |
| `conversation_messages` | `message`, `planner`, `specialist`, `reasoning_model`, `tool_used`, `tokens`, `latency` |

## Duplicated

No duplicate tables were created for existing functionality.

Important distinction:

- `specialists` does not replace or duplicate `agents`. `agents` remains the legacy/operational execution table. `specialists` is the v4 hidden specialist registry with prompts, memory scope, knowledge scope, capability scope, and voice flags.
- `founder_memory`, `business_memory`, `specialist_memory`, `conversation_memory`, and `learning_memory` do not replace `memories` or `founder_operational_learning`; they normalize future v4 memory writes without deleting existing records.

## Deprecated Or Lower-Fit Structures

| Structure | Reason |
|---|---|
| `chief_conversations`, `chief_messages` | Older chief-of-staff conversation surface; keep for backward compatibility, but v4 should use `conversation_sessions` and `conversation_messages`. |
| `agents` as founder-facing surface | Too small for specialist workspace requirements and should not answer the Founder directly. |
| `memories` as one shared memory table | Useful legacy store, but not sufficiently normalized for v4 memory isolation. |

## Final Gap Result

After applying migration `026_pardha_4_database_foundation.sql`, required v4 entities and required listed columns are present. Gap check result: no missing required tables or columns.
