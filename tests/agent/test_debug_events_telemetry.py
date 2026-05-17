"""Tests for ``debug_events`` → run_metadata aggregation."""

from __future__ import annotations

from science_graphrag.agent.debug_events_telemetry import (
    extract_runtime_telemetry_from_debug_events,
)


def test_tool_search_result_accumulates_schema_bytes_saved() -> None:
    evs = [
        {
            "type": "tool_search_result",
            "deferred_schema_refs": [{"tool": "x"}],
            "tool_schema_bytes_saved": 120,
        },
        {
            "type": "tool_search_result",
            "deferred_schema_refs": [{"tool": "y"}],
            "tool_schema_bytes_saved": 30,
        },
    ]
    tel = extract_runtime_telemetry_from_debug_events(evs)
    assert tel.get("tool_schema_bytes_saved") == 150


def test_tool_message_compact_audit_emits_microcompact_count() -> None:
    """Summing microcompact triggers across multiple compact audit events."""
    evs = [
        {"type": "tool_message_compact_audit", "tool_message_microcompact_triggered_count": 1},
        {"type": "tool_message_compact_audit", "tool_message_microcompact_triggered_count": 1},
    ]
    tel = extract_runtime_telemetry_from_debug_events(evs)
    assert tel.get("tool_message_microcompact_triggered_count") == 2


def test_mcp_audit_summary_rollup() -> None:
    evs = [
        {
            "type": "mcp_audit",
            "phase": "deny",
            "server": "s1",
            "ok": False,
            "deny_reason": "denylist_hit:x",
        },
        {"type": "mcp_audit", "phase": "call", "server": "s1", "tool": "t1", "ok": True},
    ]
    tel = extract_runtime_telemetry_from_debug_events(evs)
    mc = tel.get("mcp_audit_summary")
    assert isinstance(mc, dict)
    assert mc.get("event_count") == 2
    assert mc.get("deny_hits") == 1
    assert mc.get("ok_false_hits") == 1


def test_lsp_audit_summary_rollup() -> None:
    evs = [
        {"type": "lsp_audit", "operation": "definition", "ok": True, "degraded": False},
        {"type": "lsp_audit", "operation": "references", "ok": False, "degraded": True},
    ]
    tel = extract_runtime_telemetry_from_debug_events(evs)
    ls = tel.get("lsp_audit_summary")
    assert isinstance(ls, dict)
    assert ls.get("event_count") == 2
    assert ls.get("degraded_hits") == 1


def test_tool_use_summary_batch_emits_side_llm_cache_ratio_avg() -> None:
    evs = [
        {
            "type": "tool_use_summary_batch",
            "count": 2,
            "rows": [
                {
                    "side_llm_cache_read_ratio": 0.5,
                    "compression_ratio_vs_original": 1.2,
                },
                {
                    "side_llm_cache_read_tokens": 30,
                    "side_llm_cache_creation_tokens": 70,
                },
            ],
        }
    ]
    tel = extract_runtime_telemetry_from_debug_events(evs)
    assert tel.get("tool_use_summary_batch_count") == 1
    assert tel.get("tool_use_summary_row_count") == 2
    assert tel.get("tool_use_summary_side_llm_cache_read_ratio_avg") == 0.4


def test_terminal_outcome_emits_terminal_reason() -> None:
    evs = [
        {
            "type": "terminal_outcome",
            "terminal_reason": "partial_final_answer",
            "validation_status": "warn",
        }
    ]
    tel = extract_runtime_telemetry_from_debug_events(evs)
    assert tel.get("terminal_reason") == "partial_final_answer"


def test_terminal_outcome_overrides_validation_terminal_reason() -> None:
    """``terminal_outcome`` is emitted after validation and wins for telemetry."""
    evs = [
        {
            "type": "final_answer_validation",
            "verdict": {
                "status": "ok",
                "terminal_reason": "final_answer_ok",
            },
        },
        {
            "type": "terminal_outcome",
            "terminal_reason": "partial_final_answer",
            "validation_status": "warn",
        },
    ]
    tel = extract_runtime_telemetry_from_debug_events(evs)
    assert tel.get("terminal_reason") == "partial_final_answer"
    fav = tel.get("final_answer_validation")
    assert isinstance(fav, dict)
    assert fav.get("terminal_reason") == "final_answer_ok"


def test_final_answer_validation_telemetry_last_wins() -> None:
    evs = [
        {
            "type": "final_answer_validation",
            "verdict": {"status": "warn", "reasons": ["metadata_only_without_limitation"]},
        },
        {
            "type": "final_answer_validation",
            "verdict": {"status": "ok", "reasons": ["answer_ok"]},
        },
    ]
    tel = extract_runtime_telemetry_from_debug_events(evs)
    fav = tel.get("final_answer_validation")
    assert isinstance(fav, dict)
    assert fav.get("status") == "ok"


def test_tool_use_summary_batch_zero_read_tokens_yields_ratio_zero() -> None:
    """Rows with explicit ``side_llm_cache_read_tokens: 0`` and no ratio still roll up."""
    evs = [
        {
            "type": "tool_use_summary_batch",
            "count": 1,
            "rows": [
                {
                    "side_llm_cache_read_tokens": 0,
                    "compression_ratio_vs_original": 2.0,
                },
            ],
        }
    ]
    tel = extract_runtime_telemetry_from_debug_events(evs)
    assert tel.get("tool_use_summary_side_llm_cache_read_ratio_avg") == 0.0
