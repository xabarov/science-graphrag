from __future__ import annotations

from contextlib import contextmanager
from typing import Any

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


def test_build_agent_and_run_smoke() -> None:
    settings = Settings()
    agent = build_agent(
        settings=settings,
        neo4j=_FakeNeo(),  # type: ignore[arg-type]
        chunks=_FakeChunks(),  # type: ignore[arg-type]
        works=_FakeWorks(),  # type: ignore[arg-type]
    )
    out = agent.run(question="test question", workspace_id="ws1", max_tool_calls=8)
    assert out.answer
    assert isinstance(out.citations, list)
    assert len(out.tool_trace) >= 2
