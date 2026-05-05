"""Coverage of semantic ``product_step`` SSE events: every key transition in the
agent stream emits a stable, UI-localizable code (interpreting_question on
start, delegating_to_* per specialist hand-off, composing_answer before
synthesis, updating_session_memory after compaction). No LLM is exercised.

See ``docs/specs/agent-chat-v1.md`` for the contract."""

from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

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


class _FakeGraphWithRouting:
    """Minimal fake LangGraph: emits one routing entry then a final AIMessage."""

    async def astream(self, _state, config=None, stream_mode=None):  # noqa: ARG002
        yield (
            "values",
            {
                "routing_log": [
                    {
                        "from": "supervisor",
                        "to": "retrieval_agent",
                        "budget_left": 5,
                        "reason": "test",
                    }
                ],
                "messages": [],
                "debug_events": [],
            },
        )
        yield ("updates", {"chat": {"messages": [AIMessage(content="Final text.")]}})


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


def test_stream_emits_interpreting_question_once(monkeypatch) -> None:
    """`interpreting_question` is emitted exactly once at the start of a turn."""
    monkeypatch.setattr(
        agent_v2_stream_lifecycle,
        "build_retrieval_graph",
        lambda *_args, **_kwargs: _FakeGraphWithRouting(),
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

    interpreting = [
        e
        for e in events
        if e.get("type") == "product_step" and e.get("code") == "interpreting_question"
    ]
    assert len(interpreting) == 1, [e for e in events if e.get("type") == "product_step"]


def test_stream_emits_delegating_product_step_per_specialist(monkeypatch) -> None:
    """Each ``specialist_selected`` is followed by a ``delegating_to_*`` step."""
    monkeypatch.setattr(
        agent_v2_stream_lifecycle,
        "build_retrieval_graph",
        lambda *_args, **_kwargs: _FakeGraphWithRouting(),
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

    specialist_selected = [e for e in events if e.get("type") == "specialist_selected"]
    delegating = [
        e
        for e in events
        if e.get("type") == "product_step" and str(e.get("code") or "").startswith("delegating_to_")
    ]
    assert len(specialist_selected) == len(delegating), (specialist_selected, delegating)
    assert specialist_selected, "Fixture must produce at least one routing entry"
    assert delegating[0]["code"] == "delegating_to_retrieval_agent"
    assert delegating[0].get("specialist") == "retrieval_agent"


def test_stream_emits_composing_answer_before_synthesis(monkeypatch) -> None:
    """`composing_answer` arrives strictly before `answer_synthesis_started`."""
    monkeypatch.setattr(
        agent_v2_stream_lifecycle,
        "build_retrieval_graph",
        lambda *_args, **_kwargs: _FakeGraphWithRouting(),
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

    types = [e.get("type") for e in events]
    codes = [e.get("code") for e in events]
    assert "answer_synthesis_started" in types
    composing_idx = next(
        i
        for i, e in enumerate(events)
        if e.get("type") == "product_step" and e.get("code") == "composing_answer"
    )
    synth_idx = types.index("answer_synthesis_started")
    assert composing_idx < synth_idx, (composing_idx, synth_idx, codes)


def test_agent_note_disabled_by_default(monkeypatch) -> None:
    """When ``agent_note_enabled`` is False (default), no ``agent_note`` events appear."""
    monkeypatch.setattr(
        agent_v2_stream_lifecycle,
        "build_retrieval_graph",
        lambda *_args, **_kwargs: _FakeGraphWithRouting(),
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

    assert not any(e.get("type") == "agent_note" for e in events)


def test_agent_note_emitted_when_enabled_with_cap(monkeypatch) -> None:
    """With ``agent_note_enabled=True`` (and a fake generator), at most
    ``agent_note_max_per_turn`` notes are emitted."""
    call_count = {"n": 0}

    async def _fake_generate(*, kind, context, settings):  # noqa: ARG001
        call_count["n"] += 1
        return f"Note {kind} {call_count['n']}"

    # Patch the lazy import inside _emit_agent_note's local module load by patching
    # the source module directly.
    from science_graphrag.agent import notes as notes_mod

    monkeypatch.setattr(notes_mod, "maybe_generate_agent_note", _fake_generate)

    monkeypatch.setattr(
        agent_v2_stream_lifecycle,
        "build_retrieval_graph",
        lambda *_args, **_kwargs: _FakeGraphWithRouting(),
    )

    app = _build_test_app()
    client = TestClient(app)
    settings_override = Settings()
    settings_override.agent_note_enabled = True
    settings_override.agent_note_max_per_turn = 2
    client.app.dependency_overrides[get_settings] = lambda: settings_override
    client.app.dependency_overrides[get_stores] = lambda: _EMPTY_STORES
    try:
        events = _collect_sse_events(client, {"question": "What is BERT?"})
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    notes = [e for e in events if e.get("type") == "agent_note"]
    assert 1 <= len(notes) <= 2, notes
    for note in notes:
        assert note.get("kind") in {"intent", "route", "tool"}
        assert isinstance(note.get("note"), str) and note["note"].strip()


def test_shortcut_stream_emits_interpreting_and_composing() -> None:
    """The pre-agent shortcut stream (deferred-topic path) emits the same milestones."""
    app = _build_test_app()
    client = TestClient(app)
    client.app.dependency_overrides[get_settings] = lambda: Settings()
    client.app.dependency_overrides[get_stores] = lambda: _EMPTY_STORES
    try:
        events = _collect_sse_events(
            client,
            {"question": "Тему уточню следующим сообщением, пока подготовь общую структуру."},
        )
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    codes = [e.get("code") for e in events if e.get("type") == "product_step"]
    assert "interpreting_question" in codes, events
    assert "composing_answer" in codes, events
    types = [e.get("type") for e in events]
    composing_idx = next(
        i
        for i, e in enumerate(events)
        if e.get("type") == "product_step" and e.get("code") == "composing_answer"
    )
    synth_idx = types.index("answer_synthesis_started")
    assert composing_idx < synth_idx
