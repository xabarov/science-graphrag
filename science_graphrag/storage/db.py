from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from science_graphrag.storage.models_orm import Base


def get_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True)


def init_db(engine) -> None:
    Base.metadata.create_all(bind=engine)


def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
