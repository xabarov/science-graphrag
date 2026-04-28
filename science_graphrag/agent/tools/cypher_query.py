from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from science_graphrag.agent.cypher_safety import validate_readonly_cypher
from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


class CypherQueryTool(BaseAgentTool):
    name = "cypher_query"

    def __init__(self, store: Neo4jGraphStore, *, max_rows: int = 200) -> None:
        self._store = store
        self._max_rows = max_rows

    def run(self, *, query: str, params: dict[str, Any] | None = None) -> ToolResult:
        validate_readonly_cypher(query, max_limit=self._max_rows)
        rows: list[dict[str, Any]] = []
        with self._store.session() as session:
            result = session.run(query, **(params or {}))
            for idx, row in enumerate(result):
                if idx >= self._max_rows:
                    break
                rows.append(dict(row.items()))
        return ToolResult(
            payload={
                "rows": rows,
                "row_count": len(rows),
                "truncated_at": self._max_rows if len(rows) >= self._max_rows else None,
            },
            row_count=len(rows),
            truncated=len(rows) >= self._max_rows,
        )


class CypherQueryArgs(BaseModel):
    query: str = Field(
        ...,
        description=(
            "Read-only Cypher against Neo4j. Forbidden write/admin tokens match "
            "`cypher_safety.validate_readonly_cypher` (e.g. no CREATE/MERGE/DELETE/SET/DROP/REMOVE, "
            "no LOAD CSV). Node labels must be in the server's allow-list—unknown labels are "
            "rejected. Use LIMIT <= 200 (enforced). Prefer edge_search when you only need neighbors "
            "of one Work."
        ),
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Optional bound parameters for $ placeholders in the query (JSON-serializable scalars "
            "and lists only)."
        ),
    )


def _make_cypher_query_tool(store: Neo4jGraphStore, *, max_rows: int = 200) -> BaseTool:
    runtime_tool = CypherQueryTool(store, max_rows=max_rows)

    @tool("cypher_query", args_schema=CypherQueryArgs, return_direct=False)
    def cypher_query_tool(query: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run read-only Cypher when edge_search is not enough (paths, aggregates, filters).

        Use allowed node labels only. Bind $ parameters via params; keep LIMIT modest
        (<= max_rows, enforced). Before filtering ``edge_search`` by ``rel_types``, call
        ``workspace_graph_reltypes`` for the workspace — do not invent relationship type strings.

        **Positive patterns (adapt ids from tools):**

        1. One-hop Work neighborhood::

            MATCH (w:Work {id: $wid})-[r]-(n)
            RETURN type(r) AS rel_type, labels(n) AS labels, n.id AS nid
            LIMIT 40

        2. Two-hop to methods/datasets (read-only; ``Dataset`` is a valid label)::

            MATCH (w:Work {id: $wid})-[*1..2]-(n)
            WHERE n:Method OR n:Dataset
            RETURN DISTINCT n.id AS id, labels(n) AS labels
            LIMIT 40

        3. Co-citation neighborhood::

            MATCH (a:Work {id: $wid})-[:CITES]->(x:Work)<-[:CITES]-(b:Work)
            WHERE a <> b
            RETURN DISTINCT b.id AS co_cited_work
            LIMIT 40

        4. Authorship chain::

            MATCH (w:Work {id: $wid})-[:HAS_AUTHORSHIP]->(ash:Authorship)-[:OF_AUTHOR]->(auth:Author)
            RETURN auth.id AS author_id, ash.raw_author_name AS name
            LIMIT 40
        """
        result = run_tool_result_with_span(
            tool_name="cypher_query",
            tool_parameters={
                "query": query[:400],
                "params_keys": sorted(list((params or {}).keys()))[:20],
            },
            fn=lambda: runtime_tool.run(query=query, params=params),
        )
        payload = dict(result.payload)
        payload.setdefault("row_count", result.row_count)
        payload.setdefault("truncated", result.truncated)
        return payload

    return cypher_query_tool
