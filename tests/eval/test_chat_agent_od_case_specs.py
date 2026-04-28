"""Structural validation for OD chat scenario specs (PR C Task 6)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from science_graphrag.agent.chat_envelope import ANSWER_CLASSES

CHAT_AGENT_OD_CASES_DIR = (
    Path(__file__).resolve().parents[1] / "fixtures" / "benchmarks" / "chat_agent_od" / "cases"
)

EXPECTED_CASE_IDS = frozenset(
    {
        "od_chat_01_inventory",
        "od_chat_02_authors",
        "od_chat_03_method_profile",
        "od_chat_04_quote_grounding",
        "od_chat_05_relation_citation_path",
        "od_chat_06_temporal_evolution",
        "od_chat_07_method_family_compare",
        "od_chat_08_contradiction_explainer",
        "od_chat_09_gap_finder",
        "od_chat_10_grounded_idea",
        "od_chat_11_bibliography_export",
        "od_chat_12_multi_turn_followup",
    }
)

LANE_VALUES = frozenset({"baseline", "rich_od", "both"})

RICH_ONLY_CASE_IDS = frozenset(
    {
        "od_chat_03_method_profile",
        "od_chat_06_temporal_evolution",
        "od_chat_07_method_family_compare",
        "od_chat_08_contradiction_explainer",
        "od_chat_09_gap_finder",
        "od_chat_10_grounded_idea",
    }
)

ALLOWED_TYPED_PAYLOAD = frozenset(
    {
        "inventory",
        "bibliography",
        "relation_trace",
        "quote_candidates",
        "idea_suggestions",
        "citations",
    }
)

KNOWN_AGENT_TOOLS = frozenset(
    {
        "idea_search",
        "edge_search",
        "paper_quote_search",
        "final_answer",
        "cypher_query",
        "workspace_inspect",
        "paper_profile",
        "find_works",
        "format_bibliography_gost",
    }
)


def _load_case_records() -> list[tuple[Path, dict[str, Any]]]:
    paths = sorted(CHAT_AGENT_OD_CASES_DIR.glob("*.json"))
    assert paths, f"no case JSON under {CHAT_AGENT_OD_CASES_DIR}"
    out: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), path.name
        out.append((path, data))
    return out


def _turns_questions_valid(turns: Any) -> bool:
    if not isinstance(turns, list) or len(turns) < 2:
        return False
    for item in turns:
        if not isinstance(item, dict):
            return False
        if not str(item.get("question") or "").strip():
            return False
    return True


def _validate_answer_class_fields(case_id: str, spec: dict[str, Any]) -> None:
    expected = spec.get("answer_class_expected")
    allowed = spec.get("answer_classes_allowed")
    assert (
        expected is not None or allowed is not None
    ), f"{case_id}: need answer_class_expected or answer_classes_allowed"
    if expected is not None:
        assert isinstance(expected, str), case_id
        assert str(expected).strip() in ANSWER_CLASSES, f"{case_id}: unknown answer_class_expected"
    if allowed is not None:
        assert isinstance(allowed, list), case_id
        assert allowed, f"{case_id}: answer_classes_allowed non-empty list"
        for cls in allowed:
            assert isinstance(cls, str) and cls.strip(), case_id
            assert cls in ANSWER_CLASSES, f"{case_id}: unknown answer_class {cls!r}"


def _validate_expect_projection(case_id: str, spec: dict[str, Any]) -> None:
    expect = spec.get("expect")
    if not isinstance(expect, dict):
        return
    tools = expect.get("tools_any_of")
    if isinstance(tools, list):
        for tool in tools:
            assert str(tool) in KNOWN_AGENT_TOOLS, f"{case_id}: expect unknown tool {tool!r}"
    none_of = expect.get("tools_none_of")
    if isinstance(none_of, list):
        for tool in none_of:
            assert (
                str(tool) in KNOWN_AGENT_TOOLS
            ), f"{case_id}: expect unknown tools_none_of {tool!r}"
    exp_allowed = expect.get("answer_classes_allowed")
    if isinstance(exp_allowed, list):
        for cls in exp_allowed:
            assert str(cls) in ANSWER_CLASSES, f"{case_id}: expect bad answer_class {cls!r}"


def _assert_one_od_case(spec: dict[str, Any]) -> None:
    """Validate a single OD case JSON against schema and lane rules."""
    cid = str(spec.get("case_id") or "")
    assert cid in EXPECTED_CASE_IDS

    lane = str(spec.get("lane_compatibility") or "").strip()
    assert lane in LANE_VALUES, f"{cid}: bad lane_compatibility {lane!r}"

    baseline_ws = str(spec.get("baseline_workspace_id") or "").strip()
    if lane == "both":
        assert baseline_ws, f"{cid}: both lane needs baseline_workspace_id"
    if lane == "rich_od":
        assert (
            not baseline_ws
        ), f"{cid}: rich_od must not set baseline_workspace_id (got {baseline_ws!r})"

    if cid in RICH_ONLY_CASE_IDS:
        assert lane == "rich_od", f"{cid}: must be rich_od-only, got {lane}"
    else:
        assert lane == "both", f"{cid}: expected lane both, got {lane}"

    wid = str(spec.get("workspace_id") or "").strip()
    assert wid, f"{cid}: workspace_id required"

    has_query = bool(str(spec.get("query") or "").strip())
    turns = spec.get("turns")
    has_turns = _turns_questions_valid(turns)
    assert has_query or has_turns, f"{cid}: need query or multi-turn turns"
    if cid == "od_chat_12_multi_turn_followup":
        assert has_turns and not has_query, f"{cid}: must use turns only"

    _validate_answer_class_fields(cid, spec)

    for key in (
        "requires_chunks",
        "requires_neo4j_claims",
        "requires_qdrant_claim_vectors",
        "requires_methods",
        "requires_contradictions",
    ):
        assert isinstance(spec.get(key), bool), f"{cid}: {key} must be bool"

    if spec.get("requires_qdrant_claim_vectors") is True:
        assert (
            spec.get("requires_neo4j_claims") is True
        ), f"{cid}: requires_qdrant_claim_vectors implies requires_neo4j_claims"

    tools_any = spec.get("tools_any_of")
    assert isinstance(tools_any, list) and tools_any, f"{cid}: tools_any_of"
    for tool in tools_any:
        assert str(tool) in KNOWN_AGENT_TOOLS, f"{cid}: unknown tool {tool!r}"

    forbidden = spec.get("tools_must_not_use")
    assert isinstance(forbidden, list), f"{cid}: tools_must_not_use list"
    for tool in forbidden:
        assert str(tool) in KNOWN_AGENT_TOOLS, f"{cid}: unknown forbidden tool {tool!r}"

    min_cites = spec.get("min_citation_count")
    assert isinstance(min_cites, int), f"{cid}: min_citation_count int"
    assert min_cites >= 0, cid

    typed = spec.get("typed_payload_expected")
    assert isinstance(typed, list) and typed, f"{cid}: typed_payload_expected"
    for token in typed:
        assert str(token) in ALLOWED_TYPED_PAYLOAD, f"{cid}: bad typed token {token!r}"

    trace_exp = spec.get("trace_expectations")
    assert isinstance(trace_exp, dict) and trace_exp, f"{cid}: trace_expectations non-empty dict"

    review = spec.get("manual_review_focus")
    assert isinstance(review, list) and review, f"{cid}: manual_review_focus"
    assert all(isinstance(s, str) and s.strip() for s in review), cid

    _validate_expect_projection(cid, spec)


@pytest.fixture(scope="module", name="chat_agent_od_case_records")
def fixture_chat_agent_od_case_records() -> list[tuple[Path, dict[str, Any]]]:
    """All OD chat JSON specs under chat_agent_od/cases."""
    return _load_case_records()


def test_exactly_twelve_cases_with_expected_ids(
    chat_agent_od_case_records: list[tuple[Path, dict[str, Any]]],
) -> None:
    """Exactly 12 files; case_id set matches plan; stem matches case_id."""
    ids = {str(rec[1].get("case_id") or "") for rec in chat_agent_od_case_records}
    assert (
        len(chat_agent_od_case_records) == 12
    ), f"expected 12 cases, got {len(chat_agent_od_case_records)}"
    assert ids == EXPECTED_CASE_IDS
    for path, spec in chat_agent_od_case_records:
        cid = str(spec.get("case_id") or "")
        assert path.stem == cid, f"path stem {path.stem!r} != case_id {cid!r}"


def test_required_metadata_lane_and_shape(
    chat_agent_od_case_records: list[tuple[Path, dict[str, Any]]],
) -> None:
    """Schema §5.2 + lane rules; rich_od specs omit baseline_workspace_id."""
    for _path, spec in chat_agent_od_case_records:
        _assert_one_od_case(spec)


def test_contradiction_case_claim_flags(
    chat_agent_od_case_records: list[tuple[Path, dict[str, Any]]],
) -> None:
    """od_chat_08 stays the strictest claims+vectors+contradictions gate."""
    by_id = {str(spec["case_id"]): spec for _p, spec in chat_agent_od_case_records}
    c8 = by_id["od_chat_08_contradiction_explainer"]
    assert c8["requires_neo4j_claims"] is True
    assert c8["requires_qdrant_claim_vectors"] is True
    assert c8["requires_contradictions"] is True
    assert c8["requires_methods"] is True
