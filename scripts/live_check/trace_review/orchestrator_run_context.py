"""Trace-review run context: suite/profile side-effects and ``run_context`` assembly."""

from __future__ import annotations

import os
import sys
from argparse import Namespace
from typing import Any


def apply_suite_and_profile_side_effects(args: Namespace) -> None:
    """Mutate ``args`` for suite/profile defaults (public CLI contract)."""
    if args.suite == "acceptance":
        args.strict_v3_lifecycle = True
        if args.min_claim_verification_parse_rate is None:
            args.min_claim_verification_parse_rate = 0.95
        if not args.no_acceptance_summary:
            args.with_acceptance_summary = True
        if not args.with_long_thread_eval:
            args.with_long_thread_eval = True
    if args.profile == "quick":
        args.skip_e2e = True
        args.skip_multi_turn = True
    elif args.profile == "heavy":
        args.with_trace_audit = True
        args.with_phoenix = True
        args.with_db_audit = True
        if args.suite == "default":
            args.suite = "heavy"


def preflight_acceptance_workspace(args: Namespace) -> int | None:
    """Return exit code 2 when acceptance suite cannot run; else ``None``."""
    if args.suite == "acceptance" and not str(args.workspace_id or "").strip():
        print(
            "trace-review: suite=acceptance requires a non-empty --workspace-id or "
            "AGENT_LIVE_WORKSPACE_ID (required for agent_v2_fanout_probe).",
            file=sys.stderr,
        )
        return 2
    return None


def build_trace_review_feature_flags(
    merged_agent_runtime: str | None, *, with_long_thread_eval: bool
) -> dict[str, Any]:
    """Env-backed feature flag snapshot embedded in trace-review JSON."""
    return {
        "agent_runtime": merged_agent_runtime,
        "agent_rule_tool_search_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_RULE_TOOL_SEARCH_ENABLED"
        ),
        "agent_tool_search_deferred_schema_refs_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_TOOL_SEARCH_DEFERRED_SCHEMA_REFS_ENABLED"
        ),
        "agent_budget_stop_reasoning_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_BUDGET_STOP_REASONING_ENABLED"
        ),
        "agent_thread_insights_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_THREAD_INSIGHTS_ENABLED"
        ),
        "agent_thread_insights_llm_synthesis_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_THREAD_INSIGHTS_LLM_SYNTHESIS_ENABLED"
        ),
        "agent_tool_search_strict_deferred_activation_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_TOOL_SEARCH_STRICT_DEFERRED_ACTIVATION_ENABLED"
        ),
        "long_thread_eval_offline": str(bool(with_long_thread_eval)).lower(),
        "agent_claim_verification_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_CLAIM_VERIFICATION_ENABLED"
        ),
        "agent_subagent_lifecycle_enhanced_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_SUBAGENT_LIFECYCLE_ENHANCED_ENABLED"
        ),
        "agent_corpus_explore_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_CORPUS_EXPLORE_ENABLED"
        ),
        "agent_research_plan_subagent_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_RESEARCH_PLAN_SUBAGENT_ENABLED"
        ),
        "agent_tool_use_summary_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_TOOL_USE_SUMMARY_ENABLED"
        ),
        "agent_side_llm_openrouter_cache_control_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_SIDE_LLM_OPENROUTER_CACHE_CONTROL_ENABLED"
        ),
        "agent_llm_full_history_compact_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_LLM_FULL_HISTORY_COMPACT_ENABLED"
        ),
        "agent_tool_message_microcompact_time_trigger_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_TOOL_MESSAGE_MICROCOMPACT_TIME_TRIGGER_ENABLED"
        ),
        "agent_e1_retrieval_hop_evidence_gate_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_E1_RETRIEVAL_HOP_EVIDENCE_GATE_ENABLED"
        ),
        "agent_e1_retrieval_hop_min_payloads": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_E1_RETRIEVAL_HOP_MIN_PAYLOADS"
        ),
        "agent_writer_terminal_single_pass_shadow_enabled": os.environ.get(
            "SCIENCE_GRAPHRAG_AGENT_WRITER_TERMINAL_SINGLE_PASS_SHADOW_ENABLED"
        ),
    }


def build_trace_review_run_context_payload(
    args: Namespace,
    *,
    hb_sec: float,
    e2e_subprocess_timeout_sec: float | int,
    exec_stages: list[dict[str, Any]],
    run_kind: str | None,
    graph_id: str | None,
    merged_agent_runtime: str | None,
) -> dict[str, Any]:
    """Assemble ``run_context`` object stored in trace-review-v1 JSON."""
    return {
        "base_url": args.base_url.rstrip("/"),
        "workspace_id": args.workspace_id,
        "suite": args.suite,
        "profile": args.profile,
        "run_kind": run_kind,
        "graph_id": graph_id,
        "execution_diagnostics": {
            "heartbeat_interval_sec": hb_sec,
            "e2e_subprocess_timeout_sec": e2e_subprocess_timeout_sec,
            "stages": list(exec_stages),
        },
        "feature_flags": build_trace_review_feature_flags(
            merged_agent_runtime, with_long_thread_eval=bool(args.with_long_thread_eval)
        ),
    }


__all__ = [
    "apply_suite_and_profile_side_effects",
    "build_trace_review_feature_flags",
    "build_trace_review_run_context_payload",
    "preflight_acceptance_workspace",
]
