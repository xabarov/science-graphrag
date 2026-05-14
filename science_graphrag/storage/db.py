"""Low-level SQLAlchemy engine and session factory helpers."""

from __future__ import annotations

import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from science_graphrag.storage.models_orm import Base

_ENGINE_LOCK = threading.Lock()
_ENGINES: dict[str, object] = {}
_SESSION_FACTORIES: dict[str, sessionmaker] = {}


def get_engine(database_url: str):
    """Return a pooled engine for ``database_url`` (cached per normalized URL)."""
    key = str(database_url).strip()
    with _ENGINE_LOCK:
        eng = _ENGINES.get(key)
        if eng is None:
            eng = create_engine(database_url, pool_pre_ping=True)
            _ENGINES[key] = eng
        return eng


def init_db(engine) -> None:
    """Create ORM tables when missing (idempotent)."""
    Base.metadata.create_all(bind=engine)


def session_factory(engine):
    """Return a sessionmaker bound to ``engine`` (cached per engine URL)."""
    key = str(engine.url)
    with _ENGINE_LOCK:
        fac = _SESSION_FACTORIES.get(key)
        if fac is None:
            fac = sessionmaker(
                bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
            )
            _SESSION_FACTORIES[key] = fac
        return fac


def dispose_engine_for_database_url(database_url: str) -> None:
    """Remove cached engine/sessionmaker for ``database_url`` and dispose the engine.

    Used when replacing process-global services (e.g. ingest job registry) so a stale
    pool does not keep pointing at an abandoned DSN after tests or settings reload.
    """
    key = str(database_url).strip()
    with _ENGINE_LOCK:
        eng = _ENGINES.pop(key, None)
        session_key = str(eng.url) if eng is not None else None
        if session_key:
            _SESSION_FACTORIES.pop(session_key, None)
    if eng is not None:
        eng.dispose()
