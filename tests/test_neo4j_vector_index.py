from __future__ import annotations

from science_graphrag.storage.neo4j_store import Neo4jGraphStore


class _FakeSession:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def run(self, query: str, **_kwargs) -> None:
        self.queries.append(query)
        if "CREATE VECTOR INDEX work_title_emb" in query:
            raise RuntimeError("vector index unsupported")


class _FakeDriver:
    def __init__(self) -> None:
        self.session_obj = _FakeSession()

    def session(self):
        return self.session_obj

    def close(self) -> None:
        return None


def test_ensure_schema_skips_vector_index_if_unsupported() -> None:
    # pylint: disable=protected-access
    store = Neo4jGraphStore.__new__(Neo4jGraphStore)
    store._driver = _FakeDriver()  # type: ignore[attr-defined]
    store.ensure_schema()
    assert any("CREATE INDEX work_year" in q for q in store._driver.session_obj.queries)
    assert any("CREATE VECTOR INDEX work_title_emb" in q for q in store._driver.session_obj.queries)
