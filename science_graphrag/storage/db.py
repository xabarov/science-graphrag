from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from science_graphrag.storage.models_orm import Base


def get_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True)


def _ensure_documents_work_id_column(engine) -> None:
    """Add work_id to documents for existing DBs (create_all does not alter columns)."""
    url = str(engine.url)
    if url.startswith("postgresql"):
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS work_id VARCHAR(64)",
                ),
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_documents_work_id ON documents (work_id)",
                ),
            )
        return
    if url.startswith("sqlite"):
        with engine.begin() as conn:
            try:
                conn.execute(text("ALTER TABLE documents ADD COLUMN work_id VARCHAR(64)"))
            except Exception:
                pass
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_work_id ON documents (work_id)"))
        except Exception:
            pass


def init_db(engine) -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_documents_work_id_column(engine)


def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
