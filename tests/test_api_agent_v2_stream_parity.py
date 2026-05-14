"""SSE vs sync tool_trace parity when stream emits full state values."""

from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from science_graphrag.agent.context.session_store import clear_session_store_for_tests
from science_graphrag.api.agent_v2 import router as agent_v2_router
from science_graphrag.api.agent_v2_modules import stream_lifecycle as agent_v2_stream_lifecycle
from science_graphrag.api.deps import get_stores
from science_graphrag.config import Settings, get_settings


class _FakeGraph:
    async def astream(self, state, config=None, **kwargs):  # noqa: ARG002
        human = state["messages"][0]
        tc_id = "call-1"
        yield (
            "updates",
            {
                "n": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "idea_search",
                                    "args": {"query": "x"},
                                    "id": tc_id,
                                    "type": "tool",
                                }
                            ],
                        )
                    ]
                }
            },
        )
        yield (
            "updates",
            {
                "n": {
                    "messages": [
                        ToolMessage(
                            content=json.dumps({"row_count": 1}),
                            tool_call_id=tc_id,
                            name="idea_search",
                        )
                    ]
                }
            },
        )
        yield (
            "updates",
            {"n": {"messages": [AIMessage(content="done from stream")]}},
        )
        full = {
            "messages": [
                human,
                AIMessage(
                    content="",
                    tool_calls=[
                        {"name": "idea_search", "args": {"query": "x"}, "id": tc_id, "type": "tool"}
                    ],
                ),
                ToolMessage(
                    content=json.dumps({"row_count": 1}), tool_call_id=tc_id, name="idea_search"
                ),
                AIMessage(content="done from stream"),
            ],
            "workspace_id": state.get("workspace_id"),
            "citations": [],
            "tool_trace": [],
            "budget_remaining": 7,
            "metadata": dict(state.get("metadata") or {}),
            "specialist_results": {
                "retrieval_agent": [
                    {
                        "bibliography": {
                            "format": "gost",
                            "entries": ["Author. Title // Journal. — 2020."],
                            "filtered_work_ids": ["orphan-id"],
                            "warnings": ["some_work_ids_filtered"],
                        }
                    }
                ]
            },
            "current_specialist": None,
            "routing_log": [{"from": "supervisor", "to": "retrieval_agent", "budget_left": 8}],
            "debug_events": [
                {
                    "type": "tool_search_result",
                    "shortlist_ratio": 0.5,
                    "tool_search_miss_due_to_no_discovery": 2,
                    "deferred_tool_activation_rate": 0.25,
                    "deferred_schema_refs": [
                        {"tool": "idea_search", "schema_ref": "tool://idea_search"}
                    ],
                },
                {"type": "budget_stop_decision", "code": "agent_response_budget_cutoff"},
            ],
            "thread_id": state.get("thread_id"),
            "session_summary": str(state.get("session_summary") or ""),
            "answer_class": None,
            "history_digest": list(state.get("history_digest") or []),
        }
        yield ("values", full)


class _FakeGraphSpawnedRows:
    async def astream(self, state, config=None, **kwargs):  # noqa: ARG002
        human = state["messages"][0]
        yield (
            "values",
            {
                "messages": [human, AIMessage(content="spawned done")],
                "workspace_id": state.get("workspace_id"),
                "citations": [],
                "tool_trace": [],
                "budget_remaining": 5,
                "metadata": {
                    **dict(state.get("metadata") or {}),
                    "subagent_spawn_rows": [
                        {
                            "subagent_id": "ce-1",
                            "parent_turn_id": dict(state.get("metadata") or {}).get(
                                "parent_turn_id"
                            ),
                            "spawn_reason": "corpus_explore",
                            "task": {
                                "task_id": "task-ce-1",
                                "task_type": "corpus_explore",
                                "description": "Read-only corpus exploration child",
                                "execution_mode": "sync",
                                "fanout_slot": 1,
                            },
                            "task_id": "task-ce-1",
                            "task_type": "corpus_explore",
                            "description": "Read-only corpus exploration child",
                            "execution_mode": "sync",
                            "fanout_slot": 1,
                            "task_status": "completed",
                            "terminal_state": "succeeded",
                            "latency_ms": 17,
                            "failure_code": None,
                            "tokens": None,
                            "cost_usd_estimate": None,
                            "kind": "spawned",
                            "merge_provenance": {
                                "strategy": "typed_specialist_results_v3",
                                "source_kind": "corpus_explore_result",
                                "carried_keys": [
                                    "corpus_explore_results",
                                    "specialist_results_v3",
                                ],
                                "evidence_origin": "subagent:ce-1",
                                "parent_state_write": "bounded_append_only",
                            },
                            "output_pointer": "run_metadata.corpus_explore_results[0]",
                        }
                    ],
                },
                "specialist_results": {},
                "current_specialist": None,
                "routing_log": [],
                "debug_events": [],
                "thread_id": state.get("thread_id"),
                "session_summary": str(state.get("session_summary") or ""),
                "answer_class": None,
                "history_digest": list(state.get("history_digest") or []),
            },
        )


class _FakeGraphSpawnedRowsWithParentTimeout:
    async def astream(self, state, config=None, **kwargs):  # noqa: ARG002
        human = state["messages"][0]
        yield (
            "values",
            {
                "messages": [human, AIMessage(content="partial before timeout")],
                "workspace_id": state.get("workspace_id"),
                "citations": [],
                "tool_trace": [],
                "budget_remaining": 5,
                "metadata": {
                    **dict(state.get("metadata") or {}),
                    "subagent_spawn_rows": [
                        {
                            "subagent_id": "ce-timeout-1",
                            "parent_turn_id": dict(state.get("metadata") or {}).get(
                                "parent_turn_id"
                            ),
                            "spawn_reason": "corpus_explore",
                            "task_id": "task-timeout-1",
                            "task_type": "corpus_explore",
                            "description": "Read-only corpus exploration child",
                            "execution_mode": "sync",
                            "fanout_slot": 1,
                            "task_status": "running",
                            "terminal_state": "running",
                            "latency_ms": 4,
                            "failure_code": None,
                            "tokens": None,
                            "cost_usd_estimate": None,
                            "kind": "spawned",
                            "merge_provenance": {
                                "strategy": "typed_specialist_results_v3",
                                "source_kind": "corpus_explore_result",
                                "carried_keys": [
                                    "corpus_explore_results",
                                    "specialist_results_v3",
                                ],
                                "evidence_origin": "subagent:ce-timeout-1",
                                "parent_state_write": "bounded_append_only",
                            },
                            "output_pointer": "run_metadata.corpus_explore_results[0]",
                        }
                    ],
                },
                "specialist_results": {},
                "current_specialist": None,
                "routing_log": [],
                "debug_events": [],
                "thread_id": state.get("thread_id"),
                "session_summary": str(state.get("session_summary") or ""),
                "answer_class": None,
                "history_digest": list(state.get("history_digest") or []),
            },
        )
        await asyncio.sleep(1.1)


class _FakeGraphUnmappedTool:
    """Emits a tool_call whose name is not in _product_step_code_for_tool mapping (uses using_tool)."""

    async def astream(self, state, config=None, **kwargs):  # noqa: ARG002
        human = state["messages"][0]
        tc_id = "call-unmapped"
        tool_name = "non_mapped_agent_tool_xyz"
        yield (
            "updates",
            {
                "n": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": tool_name,
                                    "args": {"q": "x"},
                                    "id": tc_id,
                                    "type": "tool",
                                }
                            ],
                        )
                    ]
                }
            },
        )
        yield (
            "updates",
            {
                "n": {
                    "messages": [
                        ToolMessage(
                            content=json.dumps({"row_count": 0}),
                            tool_call_id=tc_id,
                            name=tool_name,
                        )
                    ]
                }
            },
        )
        yield (
            "updates",
            {"n": {"messages": [AIMessage(content="done unmapped")]}},
        )
        full = {
            "messages": [
                human,
                AIMessage(
                    content="",
                    tool_calls=[
                        {"name": tool_name, "args": {"q": "x"}, "id": tc_id, "type": "tool"}
                    ],
                ),
                ToolMessage(
                    content=json.dumps({"row_count": 0}), tool_call_id=tc_id, name=tool_name
                ),
                AIMessage(content="done unmapped"),
            ],
            "workspace_id": state.get("workspace_id"),
            "citations": [],
            "tool_trace": [],
            "budget_remaining": 7,
            "metadata": dict(state.get("metadata") or {}),
            "specialist_results": {},
            "current_specialist": None,
            "routing_log": [],
            "debug_events": [],
            "thread_id": state.get("thread_id"),
            "session_summary": str(state.get("session_summary") or ""),
            "answer_class": None,
            "history_digest": list(state.get("history_digest") or []),
        }
        yield ("values", full)


class _FakeGraphFinalAnswerToolOnly:
    """Writer calls the structured final_answer tool and never emits plain assistant text."""

    async def astream(self, state, config=None, **kwargs):  # noqa: ARG002
        human = state["messages"][0]
        tc_id = "call-final"
        ai = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "final_answer",
                    "args": {"answer": "ok from tool", "citations": []},
                    "id": tc_id,
                    "type": "tool",
                }
            ],
        )
        tool = ToolMessage(
            content=json.dumps({"answer": "ok from tool", "citations": []}),
            tool_call_id=tc_id,
            name="final_answer",
        )
        yield ("updates", {"writer": {"messages": [ai]}})
        yield ("updates", {"writer": {"messages": [tool]}})
        yield (
            "values",
            {
                "messages": [human, ai, tool],
                "workspace_id": state.get("workspace_id"),
                "citations": [{"work_id": "should_be_replaced"}],
                "tool_trace": [],
                "budget_remaining": 1,
                "metadata": dict(state.get("metadata") or {}),
                "specialist_results": {},
                "current_specialist": None,
                "routing_log": [{"from": "supervisor", "to": "writer_agent", "budget_left": 1}],
                "debug_events": [],
                "thread_id": state.get("thread_id"),
                "session_summary": str(state.get("session_summary") or ""),
                "answer_class": None,
                "history_digest": list(state.get("history_digest") or []),
            },
        )


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(agent_v2_router, prefix="/v2")
    return app


def _fake_store_registry() -> object:
    return type(
        "_S",
        (),
        {
            "neo4j": None,
            "qdrant_chunks": None,
            "qdrant_works": None,
            "qdrant_claims": None,
            "blob": None,
        },
    )()


def _collect_agent_sse_events(
    monkeypatch,
    graph_factory: type,
    *,
    question: str = "q",
    agent_runtime: str = "langgraph_supervisor_v1",
    extra_json: dict | None = None,
) -> list[dict]:
    """Stream POST /v2/agent/query and return parsed ``data:`` JSON objects (integration helper)."""
    monkeypatch.setattr(
        agent_v2_stream_lifecycle,
        "build_retrieval_graph",
        lambda *_a, **_k: graph_factory(),
    )
    client = TestClient(_app())
    client.app.dependency_overrides[get_settings] = lambda: Settings(agent_runtime=agent_runtime)
    client.app.dependency_overrides[get_stores] = _fake_store_registry
    payload: dict = {"question": question}
    if extra_json:
        payload.update(extra_json)
    try:
        events: list[dict] = []
        with client.stream(
            "POST",
            "/v2/agent/query",
            json=payload,
            headers={"Accept": "text/event-stream"},
        ) as resp:
            assert resp.status_code == 200
            for line in resp.iter_lines():
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()))
        return events
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)


def test_sse_emits_product_step_using_tool_for_unmapped_tools(monkeypatch) -> None:
    """Unmapped non-meta tools emit product_step with code using_tool (UI i18n headline)."""
    events = _collect_agent_sse_events(monkeypatch, _FakeGraphUnmappedTool)
    ps = [
        e
        for e in events
        if e.get("type") == "product_step"
        and e.get("code") == "using_tool"
        and e.get("tool") == "non_mapped_agent_tool_xyz"
    ]
    assert ps, "expected using_tool product_step for unmapped tool"


def test_sse_reasoning_live_status_emits_product_step_after_idea_search(monkeypatch) -> None:
    """SSE contract for UI live headline: mapped tools emit product_step right after tool_call."""
    events = _collect_agent_sse_events(monkeypatch, _FakeGraph)
    tool_idxs = [
        i
        for i, e in enumerate(events)
        if e.get("type") == "tool_call" and e.get("tool") == "idea_search"
    ]
    assert tool_idxs, "expected idea_search tool_call in SSE"
    ps_events = [
        e
        for e in events
        if e.get("type") == "product_step"
        and e.get("code") == "searching_literature"
        and e.get("tool") == "idea_search"
    ]
    assert (
        ps_events
    ), "expected product_step searching_literature for idea_search (UI headline source)"
    assert events.index(ps_events[0]) > tool_idxs[0]


def test_sse_subagent_lifecycle_includes_parent_turn_id_and_run_metadata(monkeypatch) -> None:
    """B1 observability: SSE mirrors routing legs into ``run_metadata.subagent_runs``."""
    events = _collect_agent_sse_events(monkeypatch, _FakeGraph)
    started = next(e for e in events if e.get("type") == "subagent_started")
    assert started.get("parent_turn_id")
    assert started.get("spawn_reason")
    fin_ev = [e for e in events if e.get("type") == "subagent_finished"]
    assert fin_ev
    assert fin_ev[0].get("parent_turn_id") == started.get("parent_turn_id")
    assert fin_ev[0].get("terminal_state") == "succeeded"
    fa = next(e for e in events if e.get("type") == "final_answer")
    rm = fa.get("run_metadata") or {}
    assert rm.get("parent_turn_id") == started.get("parent_turn_id")
    assert isinstance(rm.get("subagent_runs"), list)
    assert rm.get("max_parallel_subagents") >= 1
    assert rm["subagent_runs"][0]["subagent_id"] == started.get("subagent_id")


def test_sse_emits_spawned_subagent_terminal_row_from_metadata(monkeypatch) -> None:
    events = _collect_agent_sse_events(
        monkeypatch,
        _FakeGraphSpawnedRows,
        agent_runtime="langgraph_supervisor_v3",
    )
    started = next(
        e for e in events if e.get("type") == "subagent_started" and e.get("kind") == "spawned"
    )
    assert started.get("task_type") == "corpus_explore"
    assert started.get("task_id") == "task-ce-1"
    finished = next(
        e for e in events if e.get("type") == "subagent_finished" and e.get("kind") == "spawned"
    )
    assert finished.get("terminal_state") == "succeeded"
    assert (finished.get("merge_provenance") or {}).get("source_kind") == "corpus_explore_result"
    assert finished.get("output_pointer") == "run_metadata.corpus_explore_results[0]"
    fa = next(e for e in events if e.get("type") == "final_answer")
    rows = (fa.get("run_metadata") or {}).get("subagent_runs") or []
    assert any(
        row.get("kind") == "spawned"
        and row.get("task_type") == "corpus_explore"
        and row.get("output_pointer") == "run_metadata.corpus_explore_results[0]"
        for row in rows
    )


def test_sse_spawned_rows_are_patched_when_parent_finishes_after_inflight_spawn_row(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        agent_v2_stream_lifecycle,
        "build_retrieval_graph",
        lambda *_a, **_k: _FakeGraphSpawnedRowsWithParentTimeout(),
    )
    client = TestClient(_app())
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        agent_runtime="langgraph_supervisor_v3",
        agent_step_timeout_seconds=1.0,
    )
    client.app.dependency_overrides[get_stores] = _fake_store_registry
    try:
        events: list[dict] = []
        with client.stream(
            "POST",
            "/v2/agent/query",
            json={"question": "q"},
            headers={"Accept": "text/event-stream"},
        ) as resp:
            assert resp.status_code == 200
            for line in resp.iter_lines():
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()))
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    final = next(e for e in events if e.get("type") == "final_answer")
    rows = (final.get("run_metadata") or {}).get("subagent_runs") or []
    target = next(
        row
        for row in rows
        if row.get("kind") == "spawned" and row.get("subagent_id") == "ce-timeout-1"
    )
    # In this harness path parent completes normally after a stale in-flight spawned row;
    # run_metadata must not keep the child in running/pending state.
    assert target.get("terminal_state") == "succeeded"
    assert target.get("task_status") == "completed"
    assert target.get("failure_code") is None


def test_sse_final_tool_trace_matches_collect_tool_trace(monkeypatch) -> None:
    events = _collect_agent_sse_events(monkeypatch, _FakeGraph)

    types = [e.get("type") for e in events]
    assert "intent_classified" in types
    assert types.index("intent_classified") < types.index("specialist_selected")
    assert types.index("specialist_selected") < types.index("subagent_started")
    assert types.index("answer_synthesis_started") < types.index("final_answer")
    assert types.index("answer_synthesis_finished") < types.index("final_answer")
    assert "subagent_progress" in types or "tool_call" in types
    selected = next(e for e in events if e.get("type") == "specialist_selected")
    assert selected.get("run_kind") == "supervisor_specialists"
    assert selected.get("graph_id") == "supervisor_graph"

    finals = [e for e in events if e.get("type") == "final_answer"]
    assert len(finals) == 1
    trace = finals[0].get("tool_trace") or []
    tools = [t.get("tool") for t in trace if isinstance(t, dict)]
    assert "coordinator_gate" in tools
    assert "route_to_specialist" in tools
    assert "idea_search" in tools
    fa = finals[0]
    assert "some_work_ids_filtered" in (fa.get("warnings") or [])
    bib = fa.get("bibliography") or {}
    assert bib.get("filtered_work_ids") == ["orphan-id"]
    rm = fa.get("run_metadata") or {}
    assert "agent_runtime" in rm
    assert "extraction_llm_model" in rm
    assert "resolved_chat_llm_model" in rm
    assert rm.get("tool_search_shortlist_ratio_avg") == 0.5
    assert rm.get("tool_search_deferred_schema_events") == 1
    assert rm.get("tool_search_miss_due_to_no_discovery") == 2
    assert rm.get("deferred_tool_activation_rate") == 0.25
    assert "agent_response_budget_cutoff" in (rm.get("budget_stop_reasons") or [])
    assert rm.get("run_kind") == "supervisor_specialists"
    assert rm.get("graph_id") == "supervisor_graph"


def test_sse_final_answer_uses_structured_final_answer_tool(monkeypatch) -> None:
    """SSE final event must not lose answers returned via the final_answer tool."""
    monkeypatch.setattr(
        agent_v2_stream_lifecycle,
        "build_retrieval_graph",
        lambda *_a, **_k: _FakeGraphFinalAnswerToolOnly(),
    )
    client = TestClient(_app())
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        agent_runtime="langgraph_supervisor_v1"
    )
    client.app.dependency_overrides[get_stores] = lambda: type(
        "_S",
        (),
        {
            "neo4j": None,
            "qdrant_chunks": None,
            "qdrant_works": None,
            "qdrant_claims": None,
            "blob": None,
        },
    )()
    try:
        events = []
        with client.stream(
            "POST",
            "/v2/agent/query",
            json={"question": "q"},
            headers={"Accept": "text/event-stream"},
        ) as resp:
            assert resp.status_code == 200
            for line in resp.iter_lines():
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()))
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    finals = [e for e in events if e.get("type") == "final_answer"]
    assert len(finals) == 1
    assert finals[0].get("answer") == "ok from tool"
    assert finals[0].get("citations") == []


def test_sse_context_compacted_and_session_init_with_thread(monkeypatch) -> None:
    try:
        clear_session_store_for_tests()
        monkeypatch.setattr(
            agent_v2_stream_lifecycle,
            "build_retrieval_graph",
            lambda *_a, **_k: _FakeGraph(),
        )
        client = TestClient(_app())
        client.app.dependency_overrides[get_settings] = lambda: Settings(
            agent_runtime="langgraph_supervisor_v1"
        )
        client.app.dependency_overrides[get_stores] = lambda: type(
            "_S",
            (),
            {
                "neo4j": None,
                "qdrant_chunks": None,
                "qdrant_works": None,
                "qdrant_claims": None,
                "blob": None,
            },
        )()
        events = []
        with client.stream(
            "POST",
            "/v2/agent/query",
            json={"question": "q", "thread_id": "thr_sse_parity"},
            headers={"Accept": "text/event-stream"},
        ) as resp:
            assert resp.status_code == 200
            for line in resp.iter_lines():
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()))
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)
        clear_session_store_for_tests()

    types = [e.get("type") for e in events]
    assert "context_compacted" in types
    compact = next(e for e in events if e.get("type") == "context_compacted")
    assert compact.get("compaction", {}).get("kind") == "turn_digest"
    assert compact.get("compaction", {}).get("trigger") == "post_answer"
    assert "kinds" in compact.get("compaction", {})
    assert "turn_digest" in compact["compaction"]["kinds"]
    assert "digest_count" in compact.get("compaction", {})
    assert compact["compaction"].get("boundary", {}).get("status") == "idle"
    audit = compact.get("audit") or {}
    elig = audit.get("l4_eligibility") or {}
    assert elig.get("schema_version") == "l4_eligibility_v1"
    assert elig.get("eligible") is False
    assert elig.get("skip_reason") in {"disabled", "below_digest_cap"}
    finals = [e for e in events if e.get("type") == "final_answer"]
    assert len(finals) == 1
    trace = finals[0].get("tool_trace") or []
    tools = [t.get("tool") for t in trace if isinstance(t, dict)]
    assert "session_init" in tools
    assert finals[0].get("thread_id") == "thr_sse_parity"
    rm = finals[0].get("run_metadata") or {}
    comp_audit = rm.get("compaction_audit") or {}
    assert (comp_audit.get("l4_eligibility") or {}).get("skip_reason") in {
        "disabled",
        "below_digest_cap",
    }


def test_sse_history_digest_invalid_warning_and_final(monkeypatch) -> None:
    """SSE emits warning after intent_classified and history_digest_invalid on final_answer."""
    try:
        clear_session_store_for_tests()
        monkeypatch.setattr(
            agent_v2_stream_lifecycle,
            "build_retrieval_graph",
            lambda *_a, **_k: _FakeGraph(),
        )
        client = TestClient(_app())
        client.app.dependency_overrides[get_settings] = lambda: Settings(
            agent_runtime="langgraph_supervisor_v1"
        )
        client.app.dependency_overrides[get_stores] = lambda: type(
            "_S",
            (),
            {
                "neo4j": None,
                "qdrant_chunks": None,
                "qdrant_works": None,
                "qdrant_claims": None,
                "blob": None,
            },
        )()
        events = []
        with client.stream(
            "POST",
            "/v2/agent/query",
            json={
                "question": "q",
                "thread_id": "thr_digest_warn",
                "history_digest": "{not-json",
            },
            headers={"Accept": "text/event-stream"},
        ) as resp:
            assert resp.status_code == 200
            for line in resp.iter_lines():
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()))
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)
        clear_session_store_for_tests()

    warns = [e for e in events if e.get("type") == "warning"]
    assert any(w.get("code") == "history_digest_invalid" for w in warns)
    finals = [e for e in events if e.get("type") == "final_answer"]
    assert len(finals) == 1
    assert "history_digest_invalid" in (finals[0].get("warnings") or [])


class _FakeGraphUpdatesOnly:
    """Stream updates only (no ``values`` chunk) — exercises degraded compaction trigger."""

    async def astream(self, state, config=None, **_kwargs):  # noqa: ARG002
        assert isinstance(state, dict)
        yield (
            "updates",
            {"n": {"messages": [AIMessage(content="answer without values chunk")]}},
        )


def test_sse_context_compacted_degraded_trigger_without_values(monkeypatch) -> None:
    """``context_compacted`` uses degraded trigger when graph never yields ``values``."""
    try:
        clear_session_store_for_tests()
        monkeypatch.setattr(
            agent_v2_stream_lifecycle,
            "build_retrieval_graph",
            lambda *_a, **_k: _FakeGraphUpdatesOnly(),
        )
        client = TestClient(_app())
        client.app.dependency_overrides[get_settings] = lambda: Settings(
            agent_runtime="langgraph_supervisor_v1"
        )
        client.app.dependency_overrides[get_stores] = lambda: type(
            "_S",
            (),
            {
                "neo4j": None,
                "qdrant_chunks": None,
                "qdrant_works": None,
                "qdrant_claims": None,
                "blob": None,
            },
        )()
        events = []
        with client.stream(
            "POST",
            "/v2/agent/query",
            json={"question": "q", "thread_id": "thr_no_values"},
            headers={"Accept": "text/event-stream"},
        ) as resp:
            assert resp.status_code == 200
            for line in resp.iter_lines():
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()))
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)
        clear_session_store_for_tests()

    compact = next((e for e in events if e.get("type") == "context_compacted"), {})
    assert compact.get("compaction", {}).get("trigger") == "post_answer_degraded_stream"
    finals = [e for e in events if e.get("type") == "final_answer"]
    assert len(finals) == 1
    assert finals[0].get("answer") == "answer without values chunk"
