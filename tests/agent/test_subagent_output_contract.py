"""Contract tests for subagent-style writer / verification prompts (Train T2 §10.4)."""

from __future__ import annotations

from science_graphrag.agent.subagent_output_contract import (
    EVIDENCE_TRUST_DIRECTIVE,
    SYNTHESIZE_NOT_DELEGATE_DIRECTIVE,
    detect_handoff_phrase,
    maybe_prepend_handoff_warning,
    read_only_subagent_answer_matches_contract,
    research_plan_subagent_answer_matches_contract,
    verification_answer_matches_contract,
    writer_system_prompt_suffix,
)
from science_graphrag.config import Settings


def test_synthesize_directive_present_in_writer_suffix() -> None:
    st = Settings.model_construct(agent_writer_verification_output_format_enabled=False)
    s = writer_system_prompt_suffix(settings=st, writer_mode="normal")
    assert "delegate" in s.lower() or "synthesize" in s.lower()
    assert SYNTHESIZE_NOT_DELEGATE_DIRECTIVE.split()[0] in s


def test_writer_suffix_keeps_web_search_metadata_after_fetch_failures() -> None:
    st = Settings.model_construct(agent_writer_verification_output_format_enabled=False)
    s = writer_system_prompt_suffix(settings=st, writer_mode="normal")
    assert "web_search returned external_web metadata" in s
    assert "blanket refusal" in s


def test_writer_suffix_includes_evidence_trust_directive() -> None:
    st = Settings.model_construct(agent_writer_verification_output_format_enabled=False)
    s = writer_system_prompt_suffix(settings=st, writer_mode="normal")
    assert EVIDENCE_TRUST_DIRECTIVE.split()[0] in s
    assert "evidence_mode" in s
    assert "Source-quality guard" in s


def test_verification_format_block_when_flag_enabled() -> None:
    st = Settings.model_construct(agent_writer_verification_output_format_enabled=True)
    s = writer_system_prompt_suffix(settings=st, writer_mode="normal")
    assert "Scope:" in s
    assert "VERDICT:" in s


def test_verification_format_not_in_direct_mode_even_when_enabled() -> None:
    st = Settings.model_construct(agent_writer_verification_output_format_enabled=True)
    s = writer_system_prompt_suffix(settings=st, writer_mode="direct")
    assert "Scope:" not in s


def test_handoff_detection_and_warning_prepend() -> None:
    assert detect_handoff_phrase("Please continue from here with the analysis.")
    assert detect_handoff_phrase("I leave the rest to you.")
    out, warned = maybe_prepend_handoff_warning("Please continue.")
    assert warned is True
    assert "[warning: lazy-handoff-phrasing-detected]" in out


def test_verification_contract_regex() -> None:
    good = (
        "Scope: check claim X\n"
        "Result: grounded text.\n"
        "Key sources: w1, w2\n"
        "VERDICT: PASS\n"
    )
    assert verification_answer_matches_contract(good)
    bad = "Scope: x\nResult: y\nKey sources: z\n"
    assert not verification_answer_matches_contract(bad)


def test_read_only_subagent_contract_rejects_verdict_line() -> None:
    assert read_only_subagent_answer_matches_contract(
        "Scope: explore\nResult: found papers.\nKey sources: w1\n"
    )
    assert not read_only_subagent_answer_matches_contract(
        "Scope: x\nResult: y\nKey sources: z\nVERDICT: PASS\n"
    )


def test_research_plan_subagent_contract_requires_sections() -> None:
    ok = (
        "Scope: plan\nResult:\nCorpus sub-queries:\n- a\nGraph sub-queries:\n- b\n"
        "Writer spec:\n- c\nKey sources: none\n"
    )
    assert research_plan_subagent_answer_matches_contract(ok)
