"""In-process regression for POST /v2/agent/query sync JSON + CH4 thread_id."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from science_graphrag.agent.context.session_store import clear_session_store_for_tests
from science_graphrag.agent.runtime import AgentRunOutput
from science_graphrag.api.agent_v2 import router as agent_v2_router
from science_graphrag.api.deps import get_stores
from science_graphrag.config import Settings, get_settings


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(agent_v2_router, prefix="/v2")
    return app


def test_sync_json_history_digest_invalid_warning(monkeypatch) -> None:
    from science_graphrag.api import agent_v2 as agent_v2_api

    class _FakeAgent:
        def run(self, **_kwargs: object) -> AgentRunOutput:  # accepts client_idle_ms, etc.
            return AgentRunOutput(answer="ok", citations=[], tool_trace=[])

    monkeypatch.setattr(agent_v2_api, "build_agent", lambda **_k: _FakeAgent())
    client = TestClient(_app())
    client.app.dependency_overrides[get_settings] = lambda: Settings()
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
        resp = client.post(
            "/v2/agent/query",
            json={
                "question": "hello",
                "thread_id": "thr_invalid_digest",
                "history_digest": "{not-valid-json",
            },
            headers={"Accept": "application/json"},
        )
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "history_digest_invalid" in (data.get("warnings") or [])


def test_sync_json_thread_id_session_init_and_session_summary_excerpt(monkeypatch) -> None:
    from science_graphrag.agent.chat_envelope import build_chat_envelope
    from science_graphrag.agent.context.post_turn import apply_turn_digest_to_thread
    from science_graphrag.agent.graph.state import build_initial_agent_state
    from science_graphrag.agent.graph.tracing import collect_tool_trace
    from science_graphrag.api import agent_v2 as agent_v2_api

    class _FakeAgent:
        def run(
            self,
            *,
            question: str,
            workspace_id: str | None,
            max_tool_calls: int,
            answer_class_hint: str | None,
            thread_id: str | None,
            history_digest: list | None,
            client_idle_ms: int | None = None,  # noqa: ARG002 — parity with real agent.run()
            user_structured_answer: dict | None = None,  # noqa: ARG002
        ) -> AgentRunOutput:
            state = build_initial_agent_state(
                question=question,
                workspace_id=workspace_id,
                max_tool_calls=max_tool_calls,
                agent_runtime="retrieval_langgraph",
                thread_id=thread_id,
                history_digest=list(history_digest or []),
                answer_class_hint=answer_class_hint,
            )
            trace = collect_tool_trace(state)  # type: ignore[arg-type]
            answer = "sync-thread-ok"
            if thread_id:
                apply_turn_digest_to_thread(
                    thread_id=thread_id,
                    raw_user_question=question,
                    answer=answer,
                    answer_class="inventory",
                    tool_trace=trace,
                    workspace_id=workspace_id,
                )
            env = build_chat_envelope(
                state=state,
                answer=answer,
                citations=[],
                tool_trace=trace,
                answer_class_hint=answer_class_hint,
            )
            return AgentRunOutput(
                answer=answer,
                citations=[],
                tool_trace=trace,
                thread_id=thread_id,
                answer_class=str(env.get("answer_class") or "grounded_explanation"),
                evidence_summary=env.get("evidence_summary"),
                warnings=list(env.get("warnings") or []),
            )

    try:
        clear_session_store_for_tests()
        monkeypatch.setattr(agent_v2_api, "build_agent", lambda **_k: _FakeAgent())
        client = TestClient(_app())
        client.app.dependency_overrides[get_settings] = lambda: Settings()
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
        resp = client.post(
            "/v2/agent/query",
            json={
                "question": "How many papers?",
                "workspace_id": "ws1",
                "thread_id": "thr_sync_json",
            },
            headers={"Accept": "application/json"},
        )
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)
        clear_session_store_for_tests()

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("thread_id") == "thr_sync_json"
    tools = [x.get("tool") for x in (data.get("tool_trace") or []) if isinstance(x, dict)]
    assert "session_init" in tools
    excerpt = data.get("session_summary_excerpt")
    assert excerpt is not None and "How many papers?" in excerpt
    comp = (data.get("run_metadata") or {}).get("compaction")
    assert isinstance(comp, dict) and comp.get("kind") == "turn_digest"
    assert "kinds" in comp
    assert "post_turn_compaction_wall_ms" in (data.get("run_metadata") or {})


def test_sync_json_two_turns_same_thread_accumulates_excerpt(monkeypatch) -> None:
    from science_graphrag.agent.chat_envelope import build_chat_envelope
    from science_graphrag.agent.context.post_turn import apply_turn_digest_to_thread
    from science_graphrag.agent.graph.state import build_initial_agent_state
    from science_graphrag.agent.graph.tracing import collect_tool_trace
    from science_graphrag.api import agent_v2 as agent_v2_api

    class _FakeAgent:
        def run(
            self,
            *,
            question: str,
            workspace_id: str | None,
            max_tool_calls: int,
            answer_class_hint: str | None,
            thread_id: str | None,
            history_digest: list | None,
            client_idle_ms: int | None = None,  # noqa: ARG002 — parity with real agent.run()
            user_structured_answer: dict | None = None,  # noqa: ARG002
        ) -> AgentRunOutput:
            state = build_initial_agent_state(
                question=question,
                workspace_id=workspace_id,
                max_tool_calls=max_tool_calls,
                agent_runtime="retrieval_langgraph",
                thread_id=thread_id,
                history_digest=list(history_digest or []),
                answer_class_hint=answer_class_hint,
            )
            trace = collect_tool_trace(state)  # type: ignore[arg-type]
            answer = f"answer-for-{question[:12]}"
            if thread_id:
                apply_turn_digest_to_thread(
                    thread_id=thread_id,
                    raw_user_question=question,
                    answer=answer,
                    answer_class="inventory",
                    tool_trace=trace,
                    workspace_id=workspace_id,
                )
            env = build_chat_envelope(
                state=state,
                answer=answer,
                citations=[],
                tool_trace=trace,
                answer_class_hint=answer_class_hint,
            )
            return AgentRunOutput(
                answer=answer,
                citations=[],
                tool_trace=trace,
                thread_id=thread_id,
                answer_class=str(env.get("answer_class") or "grounded_explanation"),
                evidence_summary=env.get("evidence_summary"),
                warnings=list(env.get("warnings") or []),
            )

    tid = "thr_two_turn"
    try:
        clear_session_store_for_tests()
        monkeypatch.setattr(agent_v2_api, "build_agent", lambda **_k: _FakeAgent())
        client = TestClient(_app())
        client.app.dependency_overrides[get_settings] = lambda: Settings()
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
        r1 = client.post(
            "/v2/agent/query",
            json={"question": "FIRST_TURN_MARKER", "workspace_id": "ws1", "thread_id": tid},
            headers={"Accept": "application/json"},
        )
        assert r1.status_code == 200, r1.text
        r2 = client.post(
            "/v2/agent/query",
            json={
                "question": "SECOND_TURN_MARKER",
                "workspace_id": "ws1",
                "thread_id": tid,
                "history_digest": [
                    {"user": "FIRST_TURN_MARKER", "assistant": "answer-for-FIRST_TURN"}
                ],
            },
            headers={"Accept": "application/json"},
        )
        assert r2.status_code == 200, r2.text
        ex2 = r2.json().get("session_summary_excerpt") or ""
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)
        clear_session_store_for_tests()

    assert "FIRST_TURN_MARKER" in ex2
    assert "SECOND_TURN_MARKER" in ex2
