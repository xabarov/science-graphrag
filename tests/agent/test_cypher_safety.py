from __future__ import annotations

import pytest

from science_graphrag.agent.cypher_safety import CypherNotAllowedError, validate_readonly_cypher


@pytest.mark.parametrize(
    "query",
    [
        "MATCH (w:Work) RETURN w LIMIT 10",
        "MATCH (w:Work)-[:CITES]->(x:Work) RETURN w.id, x.id LIMIT 5",
        "MATCH (a:Author) RETURN a LIMIT 1",
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
