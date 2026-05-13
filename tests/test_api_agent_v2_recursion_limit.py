"""SSE coverage of LangGraph ``recursion_limit`` handling in the agent v2 stream.

Two scenarios:
- ``latest_full_state`` is present with a salvageable assistant draft -> the stream emits a
  ``warning`` with code ``agent_partial_graph_recursion_limit`` and a ``final_answer`` whose
  ``run_metadata`` contains ``salvaged_after_recursion_limit=true``.
- No salvageable state -> the stream emits a structured ``error`` event with
  ``code='agent_graph_recursion_limit'`` and ``error_class='agent_recursion_limit'``.

The sync (JSON) path also returns a graceful ``AgentQueryResponseV2`` with the
``agent_graph_recursion_limit_exceeded`` warning instead of bubbling the LangChain
``GraphRecursionError`` text and URL.
"""

from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.errors import GraphRecursionError

from science_graphrag.api.agent import router as agent_router
from science_graphrag.api.agent_v2 import router as agent_v2_router
from science_graphrag.api.agent_v2_modules import stream_lifecycle as agent_v2_stream_lifecycle
from science_graphrag.api.deps import get_stores
from science_graphrag.config import Settings, get_settings

_EMPTY_STORES = type(
    "_EmptyStores",
    (),
    {
        "neo4j": None,
        "qdrant_chunks": None,
        "qdrant_works": None,
        "qdrant_claims": None,
        "blob": None,
    },
)()


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(agent_router, prefix="/v1")
    app.include_router(agent_v2_router, prefix="/v2")
    return app


def _collect_sse_events(client: TestClient, payload: dict) -> list[dict]:
    events: list[dict] = []
    with client.stream(
        "POST",
        "/v2/agent/query",
        json=payload,
        headers={"Accept": "text/event-stream"},
    ) as resp:
        assert resp.status_code == 200, resp.text
        for line in resp.iter_lines():
            if line.startswith("data:"):
                events.append(json.loads(line[5:].strip()))
    return events


class _RecursingGraphWithSalvageState:
    """astream emits a ``values`` chunk carrying a salvageable AIMessage, then raises."""

    async def astream(self, _state, config=None, stream_mode=None):  # noqa: ARG002
        yield (
            "values",
            {
                "routing_log": [{"from": "supervisor", "to": "retrieval_agent", "reason": "route"}],
                "messages": [AIMessage(content="Partial draft from research.")],
                "debug_events": [],
                "citations": [],
                "metadata": {
                    "raw_user_question": "q",
                    "react_total_hops": 11,
                    "react_force_finalize": "react_hops_cap",
                    "parent_turn_id": "pt-rec-1",
                    "subagent_spawn_rows": [
                        {
                            "subagent_id": "ce-rec-1",
                            "parent_turn_id": "pt-rec-1",
                            "spawn_reason": "corpus_explore",
                            "task_id": "task-rec-1",
                            "task_type": "corpus_explore",
                            "description": "Read-only corpus exploration child",
                            "execution_mode": "sync",
                            "fanout_slot": 1,
                            "task_status": "running",
                            "terminal_state": "succeeded",
                            "latency_ms": 9,
                            "failure_code": None,
                            "kind": "spawned",
                            "merge_provenance": {
                                "strategy": "typed_specialist_results_v3",
                                "source_kind": "corpus_explore_result",
                            },
                            "output_pointer": "run_metadata.corpus_explore_results[0]",
                        }
                    ],
                },
            },
        )
        raise GraphRecursionError("Recursion limit reached")


class _RecursingGraphNoState:
    """astream raises ``GraphRecursionError`` immediately, no salvageable state."""

    async def astream(self, _state, config=None, stream_mode=None):  # noqa: ARG002
        if False:  # pragma: no cover - generator marker
            yield None
        raise GraphRecursionError("Recursion limit reached without state")


def test_stream_recursion_limit_with_salvage_emits_warning_and_partial_final_answer(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        agent_v2_stream_lifecycle,
        "build_retrieval_graph",
        lambda *_args, **_kwargs: _RecursingGraphWithSalvageState(),
    )
    app = _build_test_app()
    client = TestClient(app)
    client.app.dependency_overrides[get_settings] = lambda: Settings()
    client.app.dependency_overrides[get_stores] = lambda: _EMPTY_STORES
    try:
        events = _collect_sse_events(client, {"question": "What is BERT?"})
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    warnings = [
        e
        for e in events
        if e.get("type") == "warning" and e.get("code") == "agent_partial_graph_recursion_limit"
    ]
    assert warnings, [e for e in events if e.get("type") == "warning"]

    finals = [e for e in events if e.get("type") == "final_answer"]
    assert finals, events
    final = finals[-1]
    assert final.get("answer", "").strip(), final
    rm = final.get("run_metadata") or {}
    assert rm.get("salvaged_after_recursion_limit") is True, rm
    assert isinstance(rm.get("recursion_limit"), int) and rm["recursion_limit"] > 0
    assert rm.get("react_total_hops") == 11
    assert rm.get("react_force_finalize") == "react_hops_cap"

    final_warnings = list(final.get("warnings") or [])
    assert "agent_partial_graph_recursion_limit" in final_warnings
    assert "partial_after_recursion_limit" in final_warnings
    sub_rows = list((rm.get("subagent_runs") or []))
    assert any(
        row.get("kind") == "routing_leg" and row.get("terminal_state") == "failed"
        for row in sub_rows
    )
    assert any(
        row.get("kind") == "spawned"
        and row.get("subagent_id") == "ce-rec-1"
        and row.get("failure_code") == "parent_recursion_limit"
        and row.get("terminal_state") == "killed"
        and row.get("task_status") == "cancelled"
        for row in sub_rows
    )

    degraded = [e for e in events if e.get("type") == "degraded_mode"]
    assert degraded, events
    assert degraded[-1].get("schema_version") == 1
    reasons = degraded[-1].get("reasons") or []
    assert "recursion_limit_partial" in reasons
    assert "partial_after_recursion_limit" in reasons


def test_stream_recursion_limit_without_salvage_emits_structured_error_event(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        agent_v2_stream_lifecycle,
        "build_retrieval_graph",
        lambda *_args, **_kwargs: _RecursingGraphNoState(),
    )
    app = _build_test_app()
    client = TestClient(app)
    client.app.dependency_overrides[get_settings] = lambda: Settings()
    client.app.dependency_overrides[get_stores] = lambda: _EMPTY_STORES
    try:
        events = _collect_sse_events(client, {"question": "What is BERT?"})
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    errors = [e for e in events if e.get("type") == "error"]
    assert errors, events
    err = errors[-1]
    assert err.get("code") == "agent_graph_recursion_limit", err
    assert err.get("error_class") == "agent_recursion_limit", err
    assert isinstance(err.get("recursion_limit"), int)
    detail = str(err.get("detail") or "")
    assert "python.langchain.com" not in detail
    assert "Recursion limit reached" not in detail
    assert "agent graph hit recursion_limit=" in detail
    finals = [e for e in events if e.get("type") == "final_answer"]
    assert not finals, events


class _SyncAgentRaisingRecursion:
    """Stand-in for ``RetrievalAgent`` whose ``run`` raises the domain recursion error."""

    def run(self, **_kwargs):  # noqa: ANN001, ARG002
        from science_graphrag.agent.graph.errors import AgentGraphRecursionLimitExceeded

        raise AgentGraphRecursionLimitExceeded(recursion_limit=64)


def test_sync_recursion_limit_returns_friendly_response(monkeypatch) -> None:
    from science_graphrag.api import agent_v2 as agent_v2_mod

    monkeypatch.setattr(
        agent_v2_mod,
        "build_agent",
        lambda *_args, **_kwargs: _SyncAgentRaisingRecursion(),
    )

    app = _build_test_app()
    client = TestClient(app)
    client.app.dependency_overrides[get_settings] = lambda: Settings()
    client.app.dependency_overrides[get_stores] = lambda: _EMPTY_STORES
    try:
        resp = client.post("/v2/agent/query", json={"question": "Anything?"})
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert "agent_graph_recursion_limit_exceeded" in (payload.get("warnings") or [])
    assert "agent_graph_recursion_limit_exceeded" in (payload.get("product_markers") or [])
    rm = payload.get("run_metadata") or {}
    assert rm.get("agent_graph_recursion_limit_exceeded") is True
    assert isinstance(rm.get("recursion_limit"), int)
