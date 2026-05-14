"""Stable contracts for operator/live-check CLIs and compaction JSON (regression guard)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_LIVE_CHECK = _REPO / "scripts" / "live_check"


def _trace_review_parser_dests() -> frozenset[str]:
    lc = str(_LIVE_CHECK)
    if lc not in sys.path:
        sys.path.insert(0, lc)
    from trace_review.orchestrator_argparse import (  # pylint: disable=import-outside-toplevel
        build_agent_trace_review_parser,
    )

    p = build_agent_trace_review_parser()
    # argparse has no public iterator over actions; dest set is the contract under test.
    return frozenset(
        a.dest
        for a in p._actions  # pylint: disable=protected-access
        if getattr(a, "dest", None) not in (None, "help")
    )


def test_agent_trace_review_cli_dest_set_stable() -> None:
    """Public CLI surface: new flags must be intentional (update this set)."""
    assert _trace_review_parser_dests() == frozenset(
        {
            "base_url",
            "env_file",
            "workspace_id",
            "timeout",
            "suite",
            "profile",
            "skip_sse",
            "skip_multi_turn",
            "skip_e2e",
            "with_trace_audit",
            "with_phoenix",
            "with_db_audit",
            "with_compaction_turns",
            "require_compaction_after",
            "emit_merged_review",
            "compaction_mode",
            "compaction_max_retries_per_turn",
            "out_json",
            "out_md",
            "e2e_json",
            "with_long_thread_eval",
            "strict_v3_lifecycle",
            "min_claim_verification_parse_rate",
            "with_acceptance_summary",
            "no_acceptance_summary",
        }
    )


COMPACTION_REVIEW_JSON_TOP_LEVEL_KEYS = frozenset(
    {
        "review_version",
        "generated_at",
        "thread_id",
        "turns",
        "require_compaction_after",
        "mode",
        "max_retries_per_turn",
        "heartbeat_sec",
        "in_turn_heartbeat",
        "heartbeat_contract",
        "stop_reason",
        "fail_fast",
        "turn_attempts",
        "turn_reports",
        "compaction_events",
        "failed_turn",
        "failure_kind",
        "failure_reason",
        "verdict",
    }
)

HEARTBEAT_CONTRACT_KEYS = frozenset(
    {
        "version",
        "lane",
        "stderr_interval_sec",
        "in_turn_heartbeat_enabled",
        "stderr_event_kind",
        "silent_hang_threshold_sec",
    }
)


def test_compaction_review_report_contract_keys_documented() -> None:
    """Compaction lane JSON must retain W3/R3 diagnostic fields."""
    required = {
        "heartbeat_contract",
        "stop_reason",
        "fail_fast",
        "failure_kind",
        "failed_turn",
        "failure_reason",
    }
    assert required <= COMPACTION_REVIEW_JSON_TOP_LEVEL_KEYS


def test_compaction_report_builder_keys_match_contract_set() -> None:
    """``build_compaction_report_dict`` keys must match the documented compaction JSON contract."""
    lc = str(_LIVE_CHECK)
    if lc not in sys.path:
        sys.path.insert(0, lc)
    from compaction_review.report_builder import (  # pylint: disable=import-outside-toplevel
        build_compaction_report_dict,
    )

    report = build_compaction_report_dict(
        thread_id="t1",
        turns=1,
        require_compaction_after=1,
        mode="default",
        max_retries_per_turn=0,
        hb_sec=30.0,
        in_turn_hb=True,
        silent_hang_threshold_sec=180.0,
        turn_reports=[],
        turn_attempts=[],
        failure_reason=None,
        failure_kind=None,
        failed_turn=None,
        verdict={"status": "pass", "reasons": []},
    )
    assert frozenset(report.keys()) == COMPACTION_REVIEW_JSON_TOP_LEVEL_KEYS
    hb_contract = report.get("heartbeat_contract") or {}
    assert frozenset(hb_contract.keys()) == HEARTBEAT_CONTRACT_KEYS
