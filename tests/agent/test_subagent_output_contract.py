"""Contract tests for subagent-style writer / verification prompts (Train T2 §10.4)."""

from __future__ import annotations

from science_graphrag.agent.subagent_output_contract import (
    EVIDENCE_TRUST_DIRECTIVE,
    MANAGED_REPORT_SECTION_LIMITATIONS,
    MANAGED_REPORT_SECTION_SHORT,
    SYNTHESIZE_NOT_DELEGATE_DIRECTIVE,
    detect_handoff_phrase,
    managed_report_answer_matches_contract,
    maybe_prepend_handoff_warning,
    format_salvage_limitation_lines,
    merge_limitation_signals,
    parse_managed_report_from_text,
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


def test_managed_report_protocol_sections_parse() -> None:
    body = (
        f"{MANAGED_REPORT_SECTION_SHORT}: Found 3 candidate papers.\n"
        "Task outcome (detailed): Coverage is thin on 2025 benchmarks.\n"
        f"{MANAGED_REPORT_SECTION_LIMITATIONS}:\n"
        "- metadata_only for two sources\n"
        "- Next check: run web_fetch on official docs\n"
    )
    parsed = parse_managed_report_from_text(body)
    assert parsed["report_sections_present"] is True
    assert "candidate papers" in str(parsed["outcome_summary"])
    assert parsed["limitations"]
    assert parsed["next_checks"]
    assert managed_report_answer_matches_contract(body)


def test_managed_report_parser_supports_numbered_bullets() -> None:
    body = (
        "Task outcome (short): Coverage limited.\n"
        "Task outcome (detailed): Only two sources fetched.\n"
        "Open limitations / next checks:\n"
        "1. metadata_only for one source\n"
        "2) Next check: fetch official release notes\n"
    )
    parsed = parse_managed_report_from_text(body)
    assert "metadata_only" in " ".join(parsed["limitations"])
    assert parsed["next_checks"] == ["Next check: fetch official release notes"]


def test_managed_report_legacy_scope_result_fallback() -> None:
    body = "Scope: explore\nResult: Limited metadata only.\nKey sources: w1\n"
    parsed = parse_managed_report_from_text(body)
    assert parsed["outcome_summary"] == "explore"
    assert "Limited metadata" in str(parsed["outcome_detailed"])


def test_merge_limitation_signals_reads_typed_merge() -> None:
    lims, nxt = merge_limitation_signals(
        {"limitations": ["pdf unavailable"], "next_checks": ["Next check: retry fetch"]}
    )
    assert lims == ["pdf unavailable"]
    assert nxt == ["Next check: retry fetch"]


def test_format_salvage_limitation_lines_skips_directive_when_typed_present() -> None:
    lines = format_salvage_limitation_lines(
        language="en",
        limitations=["metadata_only"],
        next_checks=[],
        outcome_summary="thin coverage",
        writer_directive="Evidence merge (v3): synthesize...",
    )
    assert any("limitations:" in ln for ln in lines)
    assert not any("merge notes" in ln for ln in lines)


def test_format_salvage_limitation_lines_uses_directive_when_no_typed() -> None:
    lines = format_salvage_limitation_lines(
        language="en",
        limitations=[],
        next_checks=[],
        writer_directive="PDF_UNAVAILABLE: no safe OA URL",
    )
    assert any("merge notes" in ln for ln in lines)


def test_research_plan_subagent_contract_requires_sections() -> None:
    ok = (
        "Scope: plan\nResult:\nCorpus sub-queries:\n- a\nGraph sub-queries:\n- b\n"
        "Writer spec:\n- c\nKey sources: none\n"
    )
    assert research_plan_subagent_answer_matches_contract(ok)
