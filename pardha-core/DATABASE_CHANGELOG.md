# Database Changelog

## 026_pardha_4_database_foundation.sql

Applied to PostgreSQL on 2026-07-16.

### Type

Additive, backward-compatible migration.

### Existing Tables Extended

- `conversation_sessions`
  - Added `id`, `founder_id`, `started_at`, `ended_at`, `status`, `voice_enabled`, `current_context`.
  - Backfilled `id = conversation_id`.
  - Backfilled `started_at = created_at`.
  - Added supporting indexes.
- `conversation_messages`
  - Added `message`, `planner`, `specialist`, `reasoning_model`, `tool_used`, `tokens`, `latency`.
  - Backfilled `message = content`.
  - Added supporting indexes.

### New Tables

- `conversation_context`
- `conversation_intents`
- `specialists`
- `reasoning_models`
- `mcp_servers`
- `capability_routes`
- `founder_memory`
- `business_memory`
- `specialist_memory`
- `conversation_memory`
- `learning_memory`
- `learning_events`
- `voice_sessions`
- `execution_trace`

### Seed Data

- 11 `conversation_intents`
- 9 `specialists`
- 5 `reasoning_models`
- 1 `mcp_server`
- 5 `capability_routes`

### Data Safety

- No tables dropped.
- No tables renamed.
- No production data deleted.
- Existing primary keys preserved.
- Existing `conversation_id` and `message_id` contracts preserved.

### Validation

- Migration runner completed successfully.
- PostgreSQL table count increased from 74 to 88.
- v4 gap check returned no missing required tables or columns.
