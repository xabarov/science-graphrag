from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from langchain_core.messages import AIMessage

from science_graphrag.agent.runtime import build_agent
from science_graphrag.config import Settings


class _FakeNeo:
    @contextmanager
    def session(self):
        class _S:
            def run(self, *_args, **_kwargs):
                return []

        yield _S()

    def workspace_get(self, workspace_id: str) -> dict[str, Any] | None:
        return {"id": workspace_id, "name": "WS", "work_ids": ["w1", "w2"]}


class _FakeChunks:
    def search_similar(self, **_kwargs):
        return [{"id": "c1", "score": 0.9, "work_id": "w1", "text": "snippet"}]


class _FakeWorks:
    def search_similar_works(self, **_kwargs):
        return [{"work_id": "w1", "score": 0.7}]


class _FakeSupervisorLLM:
    """Fake supervisor LLM: route straight to writer (no real network)."""

    def invoke(self, _messages):
        """Return supervisor token choosing writer_agent."""
        return AIMessage(content="writer_agent")


class _FakeSpecialistLLM:
    """Fake specialist LLM for retrieval/graph subgraph build (bind_tools at compile)."""

    def bind_tools(self, _tools):
        """Return self as tool-bound chat model."""
        return self

    def invoke(self, _messages):
        """Return a terminal AIMessage without tool calls."""
        return AIMessage(content="done", tool_calls=[])


class _FakeWriterLLM:
    """Fake writer LLM: plain final answer without tool round-trip."""

    def bind_tools(self, _tools):
        """Return self as tool-bound chat model."""
        return self

    def invoke(self, _messages):
        """Return deterministic final assistant message."""
        return AIMessage(content="Synthesized answer.")


def test_build_agent_and_run_smoke(monkeypatch) -> None:
    """Smoke LangGraph agent run with fakes (no real LLM / network)."""
    monkeypatch.setattr(
        "science_graphrag.agent.graph.supervisor.build_chat_model",
        lambda _settings: _FakeSupervisorLLM(),
    )
    monkeypatch.setattr(
        "science_graphrag.agent.graph.nodes.retrieval_agent.build_chat_model",
        lambda _settings: _FakeSpecialistLLM(),
    )
    monkeypatch.setattr(
        "science_graphrag.agent.graph.nodes.graph_agent.build_chat_model",
        lambda _settings: _FakeSpecialistLLM(),
    )
    monkeypatch.setattr(
        "science_graphrag.agent.graph.nodes.writer_agent.build_chat_model",
        lambda _settings: _FakeWriterLLM(),
    )

    settings = Settings()
    agent = build_agent(
        settings=settings,
        stores=type(
            "_Stores",
            (),
            {
                "neo4j": _FakeNeo(),
                "qdrant_chunks": _FakeChunks(),
                "qdrant_works": _FakeWorks(),
                "qdrant_claims": None,
                "blob": None,
            },
        )(),
    )
    out = agent.run(question="test question", workspace_id="ws1", max_tool_calls=8)
    assert out.answer == "Synthesized answer."
    assert isinstance(out.citations, list)
    # Direct supervisor→writer path yields routing pseudo-step(s) only (no tool_calls in fake writer).
    assert out.tool_trace
    assert any(t.get("tool") == "route_to_specialist" for t in out.tool_trace)
