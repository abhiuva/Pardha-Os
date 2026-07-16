import os

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import declarative_base, sessionmaker

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
    from app.business.service import ensure_default_businesses

    ensure_default_businesses()
    return inspect(engine).get_table_names()
