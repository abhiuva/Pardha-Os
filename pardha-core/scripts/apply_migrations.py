import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import engine


MIGRATIONS_DIR = PROJECT_ROOT / "migrations"


def main() -> None:
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        applied = {
            row[0]
            for row in connection.execute(text("SELECT version FROM schema_migrations"))
        }

        for migration_file in migration_files:
            version = migration_file.name
            if version in applied:
                print(f"Skipping applied migration: {version}")
                continue

            print(f"Applying migration: {version}")
            connection.exec_driver_sql(migration_file.read_text())
            connection.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                {"version": version},
            )

    print("Database migrations complete.")


if __name__ == "__main__":
    main()
