# Pardha 4.0 Migration Plan

## Principles

- PostgreSQL remains the source of truth.
- Do not duplicate existing tables.
- Do not drop or rename existing tables.
- Keep old API contracts working while adding v4 metadata.
- Prefer additive columns and normalized companion tables.

## Completed

1. Inspected PostgreSQL, SQLAlchemy models, migrations, service access patterns, and current migration history.
2. Compared the current schema against the Pardha 4.0 database requirements.
3. Reused existing `conversation_sessions` and `conversation_messages`.
4. Added only missing v4 structures through `026_pardha_4_database_foundation.sql`.
5. Applied the migration to PostgreSQL.
6. Re-ran gap validation and confirmed no missing required v4 tables or columns.

## Rollout Steps

1. Backup PostgreSQL before deployment.
2. Deploy code containing updated SQLAlchemy models.
3. Run `./venv/bin/python scripts/apply_migrations.py`.
4. Verify:
   - `schema_migrations` contains `026_pardha_4_database_foundation.sql`.
   - `conversation_sessions` has v4 metadata columns.
   - `conversation_messages` has planner/specialist/model/tool/tokens/latency columns.
   - New v4 tables exist.
5. Restart backend services.
6. Validate dashboard and conversation APIs.

## Validation Checklist

- Database integrity: inspect table existence, FKs, indexes.
- Foreign keys: verify no orphan rows in v4 tables before writes are enabled.
- Migration validation: rerun migration runner; it must skip already applied migrations.
- SQLAlchemy validation: import models and run `init_db()` on a fresh test database.
- Repository/service validation: run conversation, capability, planning, runtime tests.
- API validation: `GET /conversations/status`, `GET /conversations/routing-validation`, `GET /conversations/voice-validation`.
- Dashboard validation: `npm run build`.
- Regression: full backend unittest suite.
- Duplicate table check: compare required v4 entities to existing tables before future migrations.

## Deferred Work

- Wire v4 writes into `conversation_context`, `voice_sessions`, `execution_trace`, and normalized memory tables.
- Add explicit API views for `conversation_intents`, `specialists`, `reasoning_models`, `mcp_servers`, and `capability_routes` if the dashboard needs administrative management.
- Add orphan-row validation queries to CI.
- Convert manual migrations to Alembic only if the team wants reversible migration metadata; do not mix systems without a transition plan.
