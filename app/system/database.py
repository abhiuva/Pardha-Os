from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.db import engine


PARDHA_TABLES = (
    "businesses",
    "tenants",
    "tenant_users",
    "auth_users",
    "auth_sessions",
    "auth_refresh_tokens",
    "audit_logs",
    "observability_metrics",
    "billing_subscriptions",
    "enterprise_integrations",
    "deployment_profiles",
    "ai_governance_records",
    "feature_flags",
    "agents",
    "events",
    "memories",
    "founder_operational_learning",
    "knowledge",
    "knowledge_imports",
    "agent_executions",
    "tasks",
    "projects",
    "objectives",
    "agent_collaborations",
    "agent_reasoning",
    "communication_accounts",
    "messages",
    "message_threads",
    "communication_history",
    "whatsapp_accounts",
    "whatsapp_messages",
    "whatsapp_conversations",
    "whatsapp_templates",
    "jira_projects",
    "jira_issues",
    "jira_sync_history",
    "sales_companies",
    "sales_contacts",
    "sales_leads",
    "sales_deals",
    "sales_activities",
    "marketing_campaigns",
    "marketing_content",
    "marketing_calendar_items",
    "marketing_analytics",
    "customer_profiles",
    "meeting_notes",
    "customer_timeline_entries",
    "chief_conversations",
    "chief_messages",
    "founder_goals",
    "capabilities",
    "capability_executions",
    "conversation_sessions",
    "conversation_messages",
    "conversation_timeline_events",
    "planning_goals",
    "execution_plans",
    "execution_plan_nodes",
    "plan_approvals",
    "plan_executions",
    "goal_kpis",
    "planning_timeline_events",
    "runtime_executions",
    "department_runtimes",
    "runtime_queue_items",
    "tool_runtime_invocations",
    "runtime_notifications",
    "automation_rules",
    "business_timeline_events",
)


class DatabaseStatus(BaseModel):
    connected: bool
    database_name: Optional[str]
    tables_found: List[str]
    record_counts: Dict[str, int]
    last_import_time: Optional[datetime]
    last_agent_execution: Optional[datetime]
    scheduler_status: str
    knowledge_import_status: str
    agent_status: Dict[str, int]


def database_status() -> DatabaseStatus:
    from app.agents.scheduler import scheduler_status
    from app.knowledge.importer import knowledge_watcher_status

    try:
        with engine.connect() as connection:
            database_name = (
                connection.execute(text("SELECT current_database()")).scalar_one()
                if connection.dialect.name == "postgresql"
                else engine.url.database
            )
            tables_found = sorted(inspect(connection).get_table_names())
            record_counts = {
                table_name: connection.execute(
                    text(f'SELECT COUNT(*) FROM "{table_name}"')
                ).scalar_one()
                for table_name in PARDHA_TABLES
                if table_name in tables_found
            }
            last_import_time = (
                connection.execute(text("SELECT MAX(imported_at) FROM knowledge_imports")).scalar_one()
                if "knowledge_imports" in tables_found
                else None
            )
            last_agent_execution = (
                connection.execute(
                    text("SELECT MAX(COALESCE(completed_at, started_at)) FROM agent_executions")
                ).scalar_one()
                if "agent_executions" in tables_found
                else None
            )
            active_agents = (
                connection.execute(text("SELECT COUNT(*) FROM agents WHERE lower(status) = 'active'")).scalar_one()
                if "agents" in tables_found
                else 0
            )
        return DatabaseStatus(
            connected=True,
            database_name=database_name,
            tables_found=tables_found,
            record_counts=record_counts,
            last_import_time=last_import_time,
            last_agent_execution=last_agent_execution,
            scheduler_status=scheduler_status(),
            knowledge_import_status=knowledge_watcher_status(),
            agent_status={"active": active_agents, "registered": record_counts.get("agents", 0)},
        )
    except SQLAlchemyError:
        return DatabaseStatus(
            connected=False,
            database_name=engine.url.database,
            tables_found=[],
            record_counts={},
            last_import_time=None,
            last_agent_execution=None,
            scheduler_status=scheduler_status(),
            knowledge_import_status=knowledge_watcher_status(),
            agent_status={"active": 0, "registered": 0},
        )
