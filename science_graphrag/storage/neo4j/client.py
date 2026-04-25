"""Neo4j driver management (connection pooling, session factory)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from neo4j import Driver, GraphDatabase, NotificationClassification


class _Neo4jClient:
    """Low-level driver wrapper shared by all Neo4j domain modules."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver: Driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            notifications_disabled_classifications=[NotificationClassification.UNRECOGNIZED],
            # Fail fast when Bolt is unreachable so API handlers do not hang the UI.
            connection_timeout=15.0,
            connection_acquisition_timeout=20.0,
        )

    def close(self) -> None:
        self._driver.close()

    @contextmanager
    def session(self) -> Iterator[Any]:
        with self._driver.session() as session:
            yield session

    def wipe_all(self) -> None:
        """Delete all nodes and relationships (dev / benchmark reset)."""
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
