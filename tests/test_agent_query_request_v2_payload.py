"""AgentQueryRequestV2 optional fields (UI / API contract)."""

from __future__ import annotations

from science_graphrag.api.agent_v2_modules.payloads import AgentQueryRequestV2


def test_agent_query_request_defaults() -> None:
    m = AgentQueryRequestV2(question="hi")
    assert m.agent_mode == "agent"
    assert m.web_research_enabled is None


def test_agent_query_request_accepts_ui_fields() -> None:
    m = AgentQueryRequestV2(
        question="hi",
        agent_mode="plan",
        web_research_enabled=False,
    )
    assert m.agent_mode == "plan"
    assert m.web_research_enabled is False
