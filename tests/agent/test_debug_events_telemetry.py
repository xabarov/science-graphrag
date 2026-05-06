"""Tests for ``debug_events`` → run_metadata aggregation."""

from __future__ import annotations

from science_graphrag.agent.debug_events_telemetry import (
    extract_runtime_telemetry_from_debug_events,
)


def test_tool_message_compact_audit_emits_microcompact_count() -> None:
    """Summing microcompact triggers across multiple compact audit events."""
    evs = [
        {"type": "tool_message_compact_audit", "tool_message_microcompact_triggered_count": 1},
        {"type": "tool_message_compact_audit", "tool_message_microcompact_triggered_count": 1},
    ]
    tel = extract_runtime_telemetry_from_debug_events(evs)
    assert tel.get("tool_message_microcompact_triggered_count") == 2
