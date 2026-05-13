"""Unit tests for canonical subagent lifecycle SSE payloads (W1 contract surface)."""

from __future__ import annotations

import json

from science_graphrag.agent.subagents.lifecycle_contract import (
    sse_subagent_finished_from_spawn_row,
    sse_subagent_finished_routing_leg,
    sse_subagent_started_from_spawn_row,
    sse_subagent_started_routing_leg,
)


def test_routing_leg_started_includes_spawn_reason_and_parent() -> None:
    """Routing leg start payload keeps parent/spawn fields for SSE/UI."""
    p = sse_subagent_started_routing_leg(
        subagent_id="retrieval_agent",
        parent_turn_id="pt-1",
        spawn_reason="routing",
        from_node="supervisor",
        summary="hop",
    )
    assert p["type"] == "subagent_started"
    assert p["subagent_id"] == "retrieval_agent"
    assert p["parent_turn_id"] == "pt-1"
    assert p["spawn_reason"] == "routing"
    assert p["from"] == "supervisor"
    assert p["summary"] == "hop"


def test_routing_leg_finished_merges_leg_done_fields() -> None:
    """Routing leg finish payload includes latency/spawn data from ledger row."""
    p = sse_subagent_finished_routing_leg(
        subagent_id="retrieval_agent",
        parent_turn_id="pt-1",
        terminal_state="timed_out",
        leg_done={"spawn_reason": "routing", "latency_ms": 42},
    )
    assert p["type"] == "subagent_finished"
    assert p["terminal_state"] == "timed_out"
    assert p["spawn_reason"] == "routing"
    assert p["latency_ms"] == 42


def test_spawn_row_replay_roundtrip_json_stable() -> None:
    """Spawned-row replay payloads remain JSON-serializable and field-complete."""
    row = {
        "kind": "spawned",
        "subagent_id": "sa-abc",
        "parent_turn_id": "pt-9",
        "spawn_reason": "corpus_explore",
        "terminal_state": "succeeded",
        "latency_ms": 100,
        "failure_code": None,
        "description": "d",
        "task_id": "tid-1",
        "task_type": "corpus_explore",
        "merge_provenance": {"strategy": "typed"},
        "output_pointer": None,
        "task": {"task_id": "tid-1", "task_type": "corpus_explore", "description": "d"},
    }
    s1 = sse_subagent_started_from_spawn_row(row, fallback_parent_turn_id=None)
    s2 = sse_subagent_finished_from_spawn_row(row, fallback_parent_turn_id=None)
    assert json.loads(json.dumps(s1))["kind"] == "spawned"
    assert json.loads(json.dumps(s2))["terminal_state"] == "succeeded"
    assert s2["merge_provenance"] == {"strategy": "typed"}
