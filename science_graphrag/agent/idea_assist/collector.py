from __future__ import annotations

from typing import Any

from science_graphrag.agent.tools import CypherQueryTool, EdgeSearchTool, IdeaSearchTool
from science_graphrag.agent.tools.workspace_catalog_tools import WorkspaceInspectTool
from science_graphrag.agent.trace import ToolCallTrace


def collect_idea_assist_context(
    *,
    workspace_id: str,
    seed_topic: str | None,
    mode: str,
    idea_search: IdeaSearchTool,
    cypher_query: CypherQueryTool,
    edge_search: EdgeSearchTool,
    workspace_inspect: WorkspaceInspectTool,
    trace: list[ToolCallTrace],
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    """Collect seed topic, claim rows, and contradiction rows."""
    step = 1
    seed = str(seed_topic or "").strip()
    if not seed:
        ws = workspace_inspect.run_with_trace(
            step=step,
            trace=trace,
            args_summary={"workspace_id": workspace_id, "mode": "blurb"},
            workspace_id=workspace_id,
            mode="blurb",
        )
        step += 1
        seed = str(ws.payload.get("summary") or "").strip()

    idea = idea_search.run_with_trace(
        step=step,
        trace=trace,
        args_summary={
            "q": seed[:120],
            "workspace_id": workspace_id,
            "kinds": ["chunk", "work"],
            "top_k": 10,
        },
        q=seed,
        workspace_id=workspace_id,
        kinds=["chunk", "work"],
        top_k=10,
    )
    step += 1
    work_ids = [str(item.get("work_id")) for item in (idea.payload.get("items") or []) if item.get("work_id")]
    unique_work_ids = sorted({wid for wid in work_ids if wid})

    claim_rows: list[dict[str, Any]] = []
    if unique_work_ids:
        claims_query = """
        MATCH (ws:Workspace {id: $workspace_id})-[:CONTAINS]->(w:Work)
        WHERE w.id IN $work_ids
        MATCH (w)<-[:ANCHORED_IN]-(e:Evidence)<-[:SUPPORTED_BY]-(c:Claim)
        RETURN w.id AS work_id,
               c.id AS claim_id,
               coalesce(c.normalized_text, c.text, '') AS claim_text,
               coalesce(c.polarity, 'neutral') AS polarity,
               coalesce(c.claim_type, '') AS claim_type,
               coalesce(c.confidence, 0.0) AS confidence,
               e.chunk_fingerprint AS chunk_fingerprint,
               coalesce(e.quote, '') AS quote
        ORDER BY work_id, claim_id
        LIMIT 400
        """
        claims_res = cypher_query.run_with_trace(
            step=step,
            trace=trace,
            args_summary={"workspace_id": workspace_id, "work_ids": len(unique_work_ids)},
            query=claims_query,
            params={"workspace_id": workspace_id, "work_ids": unique_work_ids},
        )
        step += 1
        claim_rows = [row for row in (claims_res.payload.get("rows") or []) if isinstance(row, dict)]

    contradiction_rows: list[dict[str, Any]] = []
    if mode in ("contradictions", "both"):
        anchor_work = unique_work_ids[0] if unique_work_ids else ""
        if anchor_work:
            rels = edge_search.run_with_trace(
                step=step,
                trace=trace,
                args_summary={
                    "node_id": anchor_work,
                    "rel_types": ["CONTRADICTS"],
                    "direction": "both",
                    "limit": 50,
                },
                node_id=anchor_work,
                rel_types=["CONTRADICTS"],
                direction="both",
                limit=50,
            )
            contradiction_rows = [
                row for row in (rels.payload.get("items") or []) if isinstance(row, dict)
            ]
    return seed, claim_rows, contradiction_rows
