"""Neo4j Work dedup audit queries (unit-level with mocks)."""

from __future__ import annotations

from unittest.mock import MagicMock

from science_graphrag.storage.neo4j_store import Neo4jGraphStore


def test_find_work_dedup_violations_merges_query_results() -> None:
    store = Neo4jGraphStore.__new__(Neo4jGraphStore)
    session = MagicMock()

    def _run(_query: str, **_kwargs):
        # Four property kinds: doi, openalex_id, fingerprint, arxiv_id
        if not hasattr(_run, "n"):
            _run.n = 0  # type: ignore[attr-defined]
        _run.n += 1  # type: ignore[attr-defined]
        if _run.n == 1:  # type: ignore[attr-defined]
            return iter([{"dedup_key": "10.1000/182", "ids": ["w-a", "w-b"]}])
        return iter([])

    session.run.side_effect = _run
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = None
    store._driver = driver

    violations = store.find_work_dedup_violations()
    assert len(violations) == 1
    assert violations[0]["kind"] == "doi"
    assert violations[0]["dedup_key"] == "10.1000/182"
    assert set(violations[0]["work_ids"]) == {"w-a", "w-b"}
