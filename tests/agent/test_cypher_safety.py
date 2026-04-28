from __future__ import annotations

import pytest

from science_graphrag.agent.cypher_safety import CypherNotAllowedError, validate_readonly_cypher


@pytest.mark.parametrize(
    "query",
    [
        "MATCH (w:Work) RETURN w LIMIT 10",
        "MATCH (w:Work)-[:CITES]->(x:Work) RETURN w.id, x.id LIMIT 5",
        "MATCH (a:Author) RETURN a LIMIT 1",
        "MATCH (w:Work)-[:CITES*1..2]->(other) WHERE other:Method OR other:Dataset "
        "RETURN DISTINCT other LIMIT 40",
        "MATCH (d:Dataset) RETURN d.id AS id LIMIT 5",
        "MATCH (w:Work)-[r:MENTIONS_METHOD]-(m:Method) RETURN type(r), m.id LIMIT 10",
    ],
)
def test_validate_readonly_cypher_allows_read_queries(query: str) -> None:
    validate_readonly_cypher(query)


@pytest.mark.parametrize(
    "query",
    [
        "MATCH (w:Work) DELETE w",
        "CREATE (w:Work {id:'x'})",
        "MERGE (w:Work {id:'x'}) RETURN w",
        "MATCH (w:Work) SET w.x = 1 RETURN w",
        "MATCH (w:UnknownLabel) RETURN w LIMIT 10",
        "MATCH (w:Work) RETURN w LIMIT 999",
    ],
)
def test_validate_readonly_cypher_rejects_forbidden_queries(query: str) -> None:
    with pytest.raises(CypherNotAllowedError):
        validate_readonly_cypher(query)


def test_validate_readonly_cypher_unknown_label_reset() -> None:
    with pytest.raises(CypherNotAllowedError) as exc:
        validate_readonly_cypher("MATCH (n:Reset) RETURN n LIMIT 1")
    assert "unknown_label" in str(exc.value)


def test_validate_readonly_cypher_dataset_label_does_not_trip_set_token() -> None:
    """Regression: ``Dataset`` must not match forbidden ``SET`` (whole-word check)."""
    validate_readonly_cypher(
        "MATCH (d:Dataset {id: $did}) RETURN d LIMIT 40",
        max_limit=200,
    )


def test_validate_readonly_cypher_limit_at_max_allowed() -> None:
    validate_readonly_cypher("MATCH (w:Work) RETURN w LIMIT 200", max_limit=200)


def test_validate_readonly_cypher_limit_one_over_max_rejected() -> None:
    with pytest.raises(CypherNotAllowedError) as exc:
        validate_readonly_cypher("MATCH (w:Work) RETURN w LIMIT 201", max_limit=200)
    assert "limit_too_high" in str(exc.value)


def test_validate_readonly_cypher_set_keyword_still_forbidden() -> None:
    with pytest.raises(CypherNotAllowedError) as exc:
        validate_readonly_cypher("MATCH (w:Work) SET w.x = 1 RETURN w LIMIT 1")
    assert "SET" in str(exc.value) or "forbidden_token" in str(exc.value)
