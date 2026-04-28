"""workspace_graph_reltypes Neo4j read tool."""

from __future__ import annotations

from unittest.mock import MagicMock

from science_graphrag.agent.tools.workspace_catalog_tools import WorkspaceGraphReltypesTool


def test_workspace_graph_reltypes_empty_workspace_returns_note() -> None:
    store = MagicMock()
    store.workspace_get.return_value = {"id": "ws-1", "work_ids": []}
    tool = WorkspaceGraphReltypesTool(store)
    r = tool.run(workspace_id="ws-1")
    assert r.payload.get("rel_types") == []
    assert r.payload.get("note") == "workspace_has_no_linked_works"
    store.session.assert_not_called()


def test_workspace_graph_reltypes_runs_distinct_query() -> None:
    store = MagicMock()
    store.workspace_get.return_value = {"id": "ws-1", "work_ids": ["a", "b"]}
    session = MagicMock()
    store.session.return_value.__enter__.return_value = session
    store.session.return_value.__exit__.return_value = None
    session.run.return_value = [{"rel_type": "CITES"}, {"rel_type": "HAS_AUTHORSHIP"}]

    tool = WorkspaceGraphReltypesTool(store)
    r = tool.run(workspace_id="ws-1", work_sample_limit=10, rel_types_limit=32)

    assert r.payload.get("rel_types") == ["CITES", "HAS_AUTHORSHIP"]
    assert r.payload.get("workspace_id") == "ws-1"
    session.run.assert_called_once()
    call_kw = session.run.call_args.kwargs
    assert "wids" in call_kw
    assert call_kw["wids"] == ["a", "b"]
