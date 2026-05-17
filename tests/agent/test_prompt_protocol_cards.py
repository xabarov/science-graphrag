"""Prompt-contract tests for smolagents Phase 1 protocol cards."""

from __future__ import annotations

from science_graphrag.agent.graph.nodes.retrieval_subgraph import (
    SYSTEM_PROMPT as RETRIEVAL_SYSTEM_PROMPT,
)
from science_graphrag.agent.graph.nodes.writer_agent import _system_prompt_for_mode
from science_graphrag.agent.graph.react_edges import FINAL_ANSWER_NUDGE_TEXT
from science_graphrag.agent.prompt_protocol_cards import (
    EXTERNAL_RESEARCH_PROTOCOL_HEADER,
)
from science_graphrag.agent.prompt_protocol_cards import FINAL_ANSWER_NUDGE_TEXT as NUDGE_FROM_CARDS
from science_graphrag.agent.prompt_protocol_cards import (
    TOOLCALLING_EXTERNAL_RESEARCH_PROTOCOL_HEADER,
    WRITER_TERMINAL_PROTOCOL_HEADER,
    build_retrieval_system_prompt,
    build_writer_terminal_protocol_block,
)
from science_graphrag.agent.subagent_output_contract import (
    NEGATIVE_CLAIM_GUARD_DIRECTIVE,
    writer_system_prompt_suffix,
)
from science_graphrag.config import Settings


def test_retrieval_prompt_includes_external_research_protocol_header() -> None:
    prompt = build_retrieval_system_prompt()
    assert EXTERNAL_RESEARCH_PROTOCOL_HEADER in prompt
    assert prompt == RETRIEVAL_SYSTEM_PROMPT


def test_retrieval_toolcalling_experiment_protocol_when_flag_on() -> None:
    st = Settings.model_construct(agent_external_research_toolcalling_experiment_enabled=True)
    prompt = build_retrieval_system_prompt(st)
    assert TOOLCALLING_EXTERNAL_RESEARCH_PROTOCOL_HEADER in prompt
    assert EXTERNAL_RESEARCH_PROTOCOL_HEADER not in prompt
    assert "exactly one tool Action" in prompt


def test_final_answer_nudge_text_centralized_in_protocol_cards() -> None:
    assert FINAL_ANSWER_NUDGE_TEXT == NUDGE_FROM_CARDS
    assert "final_answer" in FINAL_ANSWER_NUDGE_TEXT


def test_retrieval_protocol_web_scholar_pdf_clauses() -> None:
    prompt = build_retrieval_system_prompt()
    assert "web_search" in prompt and "web_fetch" in prompt
    assert "semantic_scholar_search" in prompt
    assert "read_external_pdf" in prompt
    assert "pdf_unavailable" in prompt
    assert "metadata-only" in prompt
    assert "Do not call final_answer" in prompt


def test_writer_normal_mode_includes_terminal_protocol() -> None:
    st = Settings.model_construct(agent_writer_verification_output_format_enabled=False)
    prompt = _system_prompt_for_mode("normal", settings=st)
    assert WRITER_TERMINAL_PROTOCOL_HEADER in prompt
    assert build_writer_terminal_protocol_block() in prompt
    assert "final_answer" in prompt
    assert "metadata_only" in prompt
    assert "generic refusal" in prompt.lower() or "generic" in prompt.lower()


def test_writer_terminal_protocol_partial_and_pdf_failure() -> None:
    block = build_writer_terminal_protocol_block()
    assert "partial" in block.lower()
    assert "pdf" in block.lower() or "PDF" in block


def test_writer_suffix_aligns_with_negative_claim_guard() -> None:
    st = Settings.model_construct(agent_writer_verification_output_format_enabled=False)
    suffix = writer_system_prompt_suffix(settings=st, writer_mode="normal")
    assert "## WriterEvidenceDirectives" in suffix
    assert NEGATIVE_CLAIM_GUARD_DIRECTIVE.split(":")[0] in suffix
