"""Contract tests for subagent task-notification XML + carry-back."""

from __future__ import annotations

from science_graphrag.agent.subagents.notification import (
    SubagentCarryBack,
    build_carry_back_from_specialist_results,
    build_task_notification_xml,
    parse_task_notification_xml,
    task_notification_human_message,
)


def test_task_notification_xml_roundtrip_summary() -> None:
    xml = build_task_notification_xml(
        task_id="tid-1",
        subagent_id="retrieval_agent",
        parent_turn_id="pt-9",
        status="completed",
        carry=SubagentCarryBack(summary="Found 3 papers.", result_excerpt="{}"),
        usage={"duration_ms": 42, "tokens_input": 10, "tokens_output": 2},
    )
    assert 'task-id="tid-1"' in xml
    assert "retrieval_agent" in xml
    assert "Found 3 papers." in xml
    parsed = parse_task_notification_xml(xml)
    assert parsed is not None
    assert parsed.get("task_id") == "tid-1"
    assert parsed.get("subagent_id") == "retrieval_agent"


def test_human_message_additional_kwargs() -> None:
    msg = task_notification_human_message(
        task_id="t2",
        subagent_id="graph_agent",
        parent_turn_id="pt-1",
        status="completed",
        carry=SubagentCarryBack(summary="ok"),
        usage=None,
    )
    ak = msg.additional_kwargs or {}
    assert ak.get("kind") == "task_notification"
    assert isinstance(ak.get("task_notification"), dict)


def test_carry_back_bounded_from_specialist_results() -> None:
    rows = [{"bibliography": {"entries": ["a", "b"], "filtered_work_ids": ["x"]}}]
    cb = build_carry_back_from_specialist_results(rows, max_chars=100)
    assert "bibliography" in cb.summary.lower() or "entries" in cb.summary
