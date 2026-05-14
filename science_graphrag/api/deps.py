from __future__ import annotations

from fastapi import Depends, Request

from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.stores.registry import (
    StoreRegistry,
    build_store_registry_for_tests,
    close_store_registry,
    init_store_registry,
)


def get_stores(request: Request) -> StoreRegistry:
    """FastAPI dependency returning app-level store registry."""

    stores = getattr(request.app.state, "stores", None)
    if stores is None:
        raise RuntimeError(
            "StoreRegistry not initialized. Ensure init_store_registry() runs in app lifespan."
        )
    if not isinstance(stores, StoreRegistry):
        raise RuntimeError(f"Invalid app.state.stores type: {type(stores)!r}")
    return stores


def get_neo4j_store(stores: StoreRegistry = Depends(get_stores)) -> Neo4jGraphStore:
    """Backward-compatible dependency for endpoints that only need Neo4j."""

    return stores.neo4j


__all__ = [
    "StoreRegistry",
    "build_store_registry_for_tests",
    "close_store_registry",
    "get_neo4j_store",
    "get_stores",
    "init_store_registry",
]
