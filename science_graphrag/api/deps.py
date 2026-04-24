from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends

from science_graphrag.config import Settings, get_settings
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


def get_neo4j_store(
    settings: Settings = Depends(get_settings),
) -> Generator[Neo4jGraphStore, None, None]:
    store = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        yield store
    finally:
        store.close()
