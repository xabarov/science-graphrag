"""Agent ChatOpenAI max_retries wiring (Phase 4)."""

from __future__ import annotations

from science_graphrag.agent.llm.chat import build_chat_model
from science_graphrag.config import Settings


def test_build_chat_model_respects_agent_chat_max_retries() -> None:
    s = Settings(agent_chat_max_retries=0)
    llm = build_chat_model(s)
    assert getattr(llm, "max_retries", None) == 0


def test_build_chat_model_max_retries_override() -> None:
    s = Settings(agent_chat_max_retries=2)
    llm = build_chat_model(s, max_retries=0)
    assert getattr(llm, "max_retries", None) == 0
