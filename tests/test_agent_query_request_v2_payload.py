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


def test_agent_query_request_accepts_pdf_read_request() -> None:
    m = AgentQueryRequestV2(
        question="hi",
        pdf_read_request={"pdf_url": "https://arxiv.org/pdf/1706.03762.pdf"},
    )
    assert isinstance(m.pdf_read_request, dict)
    assert m.pdf_read_request == {"pdf_url": "https://arxiv.org/pdf/1706.03762.pdf"}
