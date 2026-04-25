"""Neo4jGraphStore facade preserving backward-compatible public API."""

from __future__ import annotations

from science_graphrag.storage.neo4j.facade_base import Neo4jGraphStoreBase
from science_graphrag.storage.neo4j.facade_delegates import Neo4jGraphStoreDelegates


class Neo4jGraphStore(Neo4jGraphStoreDelegates, Neo4jGraphStoreBase):
    """Facade over neo4j subpackage. Public API matches legacy store."""
