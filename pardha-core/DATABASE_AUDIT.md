# Pardha 4.0 Database Audit

Audit date: 2026-07-16

## Scope

This audit inspected the reachable PostgreSQL database, SQLAlchemy models, manual SQL migrations, migration history, runtime diagnostics, and current seed/demo data before adding Pardha 4.0 structures.

## Database Connection

- Primary database inspected: `postgresql+psycopg2:///pardha_core`
- Dialect: PostgreSQL
- Tables before v4 migration: 74
- Tables after v4 migration: 88
- Views: none
- Triggers: none
- Sequences: none
- Constraints after v4 migration: 218 primary key, unique, and foreign key constraints
- Migration runner: `scripts/apply_migrations.py`
- Migration history table: `schema_migrations`
- Latest applied migration: `026_pardha_4_database_foundation.sql`

## Architecture Inventory

Pardha currently uses SQLAlchemy declarative models in [app/db/models.py](/Users/abhishekkola/pardha/pardha-core/app/db/models.py) and manual SQL migrations in [migrations](/Users/abhishekkola/pardha/pardha-core/migrations). No Alembic environment is present.

Repository/service access is service-oriented rather than repository-class oriented. Domain services own persistence access through `SessionLocal`, including:

- Conversation runtime: `app/conversations/service.py`
- Capability registry: `app/capabilities/service.py`
- Business context: `app/business/service.py`
- Knowledge: `app/knowledge/service.py`
- Planning/runtime: `app/planning/service.py`, `app/runtime/service.py`
- Sales/Marketing: `app/sales/service.py`, `app/marketing/service.py`
- Enterprise/auth: `app/enterprise/service.py`, `app/auth/service.py`

## Table Inventory

| Area | Tables |
|---|---|
| Tenant/Auth/Enterprise | `tenants`, `tenant_users`, `auth_users`, `auth_sessions`, `auth_refresh_tokens`, `audit_logs`, `billing_subscriptions`, `enterprise_integrations`, `deployment_profiles`, `ai_governance_records`, `feature_flags`, `observability_metrics` |
| Businesses/Knowledge/Memory | `businesses`, `knowledge`, `knowledge_imports`, `memories`, `founder_operational_learning`, `founder_memory`, `business_memory`, `specialist_memory`, `conversation_memory`, `learning_memory` |
| Conversations | `conversation_sessions`, `conversation_messages`, `conversation_timeline_events`, `conversation_context`, `conversation_intents` |
| Specialists/Reasoning/MCP | `agents`, `specialists`, `reasoning_models`, `mcp_servers`, `capability_routes`, `capabilities`, `capability_executions` |
| Planning/Runtime | `planning_goals`, `execution_plans`, `execution_plan_nodes`, `plan_approvals`, `plan_executions`, `goal_kpis`, `planning_timeline_events`, `runtime_executions`, `department_runtimes`, `runtime_queue_items`, `tool_runtime_invocations`, `runtime_notifications`, `automation_rules`, `execution_trace` |
| Product/Engineering | `projects`, `software_factory_requirements`, `software_factory_artifacts`, `software_factory_approvals`, `jira_projects`, `jira_issues`, `jira_sync_history` |
| Sales/Marketing/CS | `sales_companies`, `sales_contacts`, `sales_leads`, `sales_deals`, `sales_activities`, `marketing_campaigns`, `marketing_content`, `marketing_calendar_items`, `marketing_analytics`, `customer_profiles`, `meeting_notes`, `customer_timeline_entries` |
| Communications | `communication_accounts`, `message_threads`, `messages`, `communication_history`, `whatsapp_accounts`, `whatsapp_conversations`, `whatsapp_templates`, `whatsapp_messages` |
| Legacy/Agent Collaboration | `agents`, `events`, `agent_executions`, `agent_reasoning`, `tasks`, `objectives`, `agent_collaborations`, `chief_conversations`, `chief_messages`, `founder_goals`, `business_timeline_events` |

## Current Seed/Demo Data

Live local PostgreSQL has seeded/default rows in key registries after v4 migration:

- `conversation_intents`: 11 records
- `specialists`: 9 records
- `reasoning_models`: 5 records
- `mcp_servers`: 1 record
- `capability_routes`: 5 records

The SQLite local runtime database also contains demo operating data, but PostgreSQL is treated as the source of truth for this audit.

## Migration Inventory

Manual migrations currently run from `001_create_knowledge.sql` through `026_pardha_4_database_foundation.sql`.

Important architecture milestones:

- `010_create_business_context.sql`: business scoping added to existing data.
- `018_create_capability_registry.sql`: capability registry and execution table.
- `019_create_conversation_engine.sql`: original conversation sessions/messages/timeline.
- `020_create_planning_engine.sql`: planning goals, plans, approvals, KPIs.
- `021_create_universal_runtime.sql`: runtime queue, execution, tool invocation, notifications.
- `023_create_enterprise_platform.sql`: tenants, auth, audit, billing, governance.
- `024_rc1_postgres_reconciliation.sql`: PostgreSQL reconciliation and non-destructive FKs.
- `025_conversation_hardening.sql`: founder operational learning.
- `026_pardha_4_database_foundation.sql`: v4 executive assistant foundation.

## Findings

- Existing conversation tables were reused and extended; they were not duplicated.
- Existing `agents` table is too small for the v4 specialist workspace requirement, so `specialists` was added as a richer registry while preserving `agents`.
- Existing `founder_operational_learning` remains valid; normalized memory tables were added for v4 separation without copying or deleting data.
- Existing `capabilities` and `tool_runtime_invocations` remain valid; `capability_routes` and `mcp_servers` were added to make routing explicit.
- No destructive operations were performed.
