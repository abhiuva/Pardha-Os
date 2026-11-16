import os
from urllib.parse import urlparse, urlunparse

import psycopg2
from sqlalchemy.engine import make_url

from app.db import DATABASE_URL
from app.db import engine
from app.db.models import Base as ModelsBase


def _database_exists(connection_url, database_name):
    with psycopg2.connect(connection_url) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (database_name,),
            )
            return cursor.fetchone() is not None


def _create_database(connection_url, database_name):
    with psycopg2.connect(connection_url) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE \"{database_name}\"")


def main() -> None:
    parsed = make_url(DATABASE_URL)
    database_name = parsed.database
    if not database_name:
        raise ValueError("DATABASE_URL must contain a database name")

    admin_url = parsed.set(database="postgres")
    admin_connection_url = str(admin_url)

    if not _database_exists(admin_connection_url, database_name):
        print(f"Creating database '{database_name}'")
        _create_database(admin_connection_url, database_name)
    else:
        print(f"Database '{database_name}' already exists")

    print("Creating database tables...")
    ModelsBase.metadata.create_all(bind=engine)
    print("Database initialization complete.")


if __name__ == "__main__":
    main()
