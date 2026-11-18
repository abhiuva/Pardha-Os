import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.db.safety import enforce_test_database_policy

# Test runs must never fall back to the developer database: check the raw setting
# before the default is applied and before any engine exists.
enforce_test_database_policy(os.getenv("DATABASE_URL"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2:///pardha_core",
)

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db() -> list[str]:
    from app.db.models import Base as ModelsBase

    ModelsBase.metadata.create_all(bind=engine)
    _reconcile_sqlite_schema()
    from app.business.service import ensure_default_businesses

    ensure_default_businesses()
    return inspect(engine).get_table_names()


def _reconcile_sqlite_schema() -> None:
    if engine.dialect.name != "sqlite":
        return
    additions = {
        "conversation_sessions": {
            "id": "VARCHAR(36)",
            "founder_id": "VARCHAR(36)",
            "started_at": "DATETIME",
            "ended_at": "DATETIME",
            "status": "VARCHAR NOT NULL DEFAULT 'active'",
            "voice_enabled": "INTEGER NOT NULL DEFAULT 0",
            "current_context": "JSON DEFAULT '{}'",
        },
        "conversation_messages": {
            "message": "TEXT",
            "planner": "VARCHAR",
            "specialist": "VARCHAR",
            "reasoning_model": "VARCHAR",
            "tool_used": "VARCHAR",
            "tokens": "INTEGER NOT NULL DEFAULT 0",
            "latency": "INTEGER NOT NULL DEFAULT 0",
        },
        "agent_reasoning": {
            "provider_metadata": "JSON DEFAULT '{}'",
        },
    }
    with engine.begin() as connection:
        inspector = inspect(connection)
        existing_tables = set(inspector.get_table_names())
        for table_name, columns in additions.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, ddl in columns.items():
                if column_name not in existing_columns:
                    connection.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {ddl}'))
        if "conversation_sessions" in existing_tables:
            connection.execute(text("UPDATE conversation_sessions SET id = conversation_id WHERE id IS NULL"))
            connection.execute(text("UPDATE conversation_sessions SET started_at = created_at WHERE started_at IS NULL"))
        if "conversation_messages" in existing_tables:
            connection.execute(text("UPDATE conversation_messages SET message = content WHERE message IS NULL"))
