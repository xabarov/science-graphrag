"""Core Neo4j client wiring and legacy test adapter."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from science_graphrag.storage.neo4j import schema
from science_graphrag.storage.neo4j.client import _Neo4jClient


class _LegacyDriverClientAdapter:
    """Compatibility adapter for tests that monkeypatch `Neo4jGraphStore._driver`."""

    def __init__(self, driver: Any) -> None:
        self._driver = driver

    @contextmanager
    def session(self) -> Iterator[Any]:
        with self._driver.session() as session:
            yield session

    def close(self) -> None:
        self._driver.close()

    def wipe_all(self) -> None:
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")


class Neo4jGraphStoreBase:
    """Holds Neo4j client lifecycle; delegate methods live in ``facade_delegates``."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._client = _Neo4jClient(uri, user, password)

    @property
    def _client(self) -> _Neo4jClient | _LegacyDriverClientAdapter:  # type: ignore[misc]
        client = self.__dict__.get("__client")
        if client is not None:
            return client
        driver = self.__dict__.get("_driver")
        if driver is not None:
            return _LegacyDriverClientAdapter(driver)
        raise AttributeError("Neo4jGraphStore is not initialized")

    @_client.setter
    def _client(self, value: _Neo4jClient) -> None:
        self.__dict__["__client"] = value
        self.__dict__["_driver"] = value._driver  # legacy compatibility for tests

    def close(self) -> None:
        self._client.close()

    def session(self):
        return self._client.session()

    def wipe_all(self) -> None:
        self._client.wipe_all()

    def ensure_schema(self) -> None:
        schema.ensure_schema(self._client)
