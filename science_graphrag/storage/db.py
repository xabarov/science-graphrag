from __future__ import annotations

import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from science_graphrag.storage.models_orm import Base

_ENGINE_LOCK = threading.Lock()
_ENGINES: dict[str, object] = {}
_SESSION_FACTORIES: dict[str, sessionmaker] = {}


def get_engine(database_url: str):
    key = str(database_url).strip()
    with _ENGINE_LOCK:
        eng = _ENGINES.get(key)
        if eng is None:
            eng = create_engine(database_url, pool_pre_ping=True)
            _ENGINES[key] = eng
        return eng


def init_db(engine) -> None:
    Base.metadata.create_all(bind=engine)


def session_factory(engine):
    key = str(engine.url)
    with _ENGINE_LOCK:
        fac = _SESSION_FACTORIES.get(key)
        if fac is None:
            fac = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
            _SESSION_FACTORIES[key] = fac
        return fac
