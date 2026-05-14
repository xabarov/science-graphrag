"""Core execution path for ``agent_trace_review`` (split from entrypoint for size)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .orchestrator_env import e2e_subprocess_timeout_sec as _e2e_subprocess_timeout_sec
from .orchestrator_env import ensure_local_imports as _ensure_local_imports
from .orchestrator_env import load_dotenv as _load_dotenv
from .orchestrator_env import runtime_attribution_from_env as _runtime_attribution_from_env
from .orchestrator_env import (
    runtime_attribution_from_runtime_id as _runtime_attribution_from_runtime_id,
)
from .orchestrator_env import (
    trace_review_heartbeat_interval_s as _trace_review_heartbeat_interval_s,
)
from .orchestrator_report import checks_dict as _checks_dict
from .orchestrator_report import json_safe_value as _json_safe_value
from .orchestrator_report import (
    patch_run_context_execution_diagnostics as _patch_run_context_execution_diagnostics,
)
from .orchestrator_report import (
    server_agent_runtime_from_checks as _server_agent_runtime_from_checks,
)
from .orchestrator_report import sse_missing_final as _sse_missing_final
from .orchestrator_report import write_markdown as _write_markdown
from .orchestrator_stage_runner import execute_trace_stage as _execute_trace_stage
from .orchestrator_subprocess import run_compaction_turn_review as _run_compaction_turn_review
from .orchestrator_subprocess import run_http_suite as _run_http_suite
from .orchestrator_subprocess import run_optional_e2e as _run_optional_e2e
from .orchestrator_subprocess import run_phoenix_pull as _run_phoenix_pull


def run_agent_trace_review(args: Namespace) -> int:
    """Execute trace-review pipeline; mutates ``args`` for profile/suite side-effects."""
    _ensure_local_imports()
    from dotenv_util import (  # pylint: disable=import-outside-toplevel,import-error
        resolve_live_base_url,
    )
    from trace_review_schema import (  # pylint: disable=import-outside-toplevel
        REVIEW_VERSION,
        TraceReviewV1,
        aggregate_metrics_from_timeline,
        build_acceptance_summary,
        check_from_dict,
        e2e_failures_are_retryable_provider_flakes,
        merge_e2e_report_json_into_review,
        trace_review_to_dict,
        verdict_from_signals,
    )

    _load_dotenv(args.env_file)
    args.base_url = resolve_live_base_url(args.base_url)
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

    if args.suite == "acceptance" and not str(args.workspace_id or "").strip():
        print(
            "trace-review: suite=acceptance requires a non-empty --workspace-id or "
            "AGENT_LIVE_WORKSPACE_ID (required for agent_v2_fanout_probe).",
            file=sys.stderr,
        )
        return 2

    hb_sec = _trace_review_heartbeat_interval_s()
    exec_stages: list[dict[str, Any]] = []
    e2e_subprocess_timeout_sec = _e2e_subprocess_timeout_sec()
    print(
        f"[trace-review] run_start suite={args.suite} profile={args.profile} "
        f"heartbeat_sec={hb_sec} e2e_subprocess_timeout_sec={e2e_subprocess_timeout_sec!r}",
        file=sys.stderr,
        flush=True,
    )

    checks = _execute_trace_stage(
        exec_stages,
        "http_suite",
        lambda: _run_http_suite(
            base_url=args.base_url.rstrip("/"),
            workspace_id=args.workspace_id,
            timeout=args.timeout,
            skip_sse=args.skip_sse,
            skip_multi_turn=args.skip_multi_turn,
            extended_safety=(args.suite == "acceptance"),
        ),
        heartbeat_interval_s=hb_sec,
    )

    report_json_path: Path | None = None
    if not args.skip_e2e:
        tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115
            suffix=".json",
            delete=False,
            prefix="e2e_full_report_",
        )
        tmp.close()
        report_json_path = Path(tmp.name)

    e2e = _execute_trace_stage(
        exec_stages,
        "e2e_audit_subprocess",
        lambda: _run_optional_e2e(
            args,
            report_json_path,
            subprocess_timeout=e2e_subprocess_timeout_sec,
        ),
        heartbeat_interval_s=hb_sec,
    )

    def _merge_timeline() -> Any:
        merged = merge_e2e_report_json_into_review(cases=[], workspace_postgres=None)
        if report_json_path and report_json_path.exists() and not args.skip_e2e:
            try:
                report_obj = json.loads(report_json_path.read_text(encoding="utf-8"))
                cases = report_obj.get("cases") or []
                if isinstance(cases, list):
                    postgres_blob = report_obj.get("postgres_ingest_jobs")
                    merged = merge_e2e_report_json_into_review(
                        cases=[x for x in cases if isinstance(x, dict)],
                        workspace_postgres=(
                            postgres_blob if isinstance(postgres_blob, dict) else None
                        ),
                    )
            except (OSError, json.JSONDecodeError):
                merged = merge_e2e_report_json_into_review(cases=[], workspace_postgres=None)
        return merged

    trace_timeline = _execute_trace_stage(
        exec_stages,
        "merge_e2e_report_json",
        _merge_timeline,
        heartbeat_interval_s=hb_sec,
    )

    phoenix_snap_path: str | None = None
    phoenix_pull_meta: dict[str, Any] | None = None
    if args.with_phoenix and report_json_path and report_json_path.exists() and not args.skip_e2e:
        try:
            report_obj = json.loads(report_json_path.read_text(encoding="utf-8"))
            tids: list[str] = []
            for c in report_obj.get("cases") or []:
                if not isinstance(c, dict):
                    continue
                tid = (c.get("phoenix_trace_id") or "").strip()
                if tid:
                    tids.append(tid)
            snap_path = args.out_json.parent / f"{args.out_json.stem}_phoenix_spans.jsonl"

            def _phoenix_pull() -> dict[str, Any]:
                return _run_phoenix_pull(tids, snap_path, timeout=min(60.0, args.timeout))

            phoenix_pull_meta = _execute_trace_stage(
                exec_stages,
                "phoenix_trace_pull",
                _phoenix_pull,
                heartbeat_interval_s=hb_sec,
            )
            if snap_path.exists():
                phoenix_snap_path = str(snap_path)
        except (OSError, json.JSONDecodeError):
            phoenix_pull_meta = {"ok": False, "error": "report_parse_failed"}

    metrics = aggregate_metrics_from_timeline(trace_timeline)

    chk_map = _checks_dict(checks)
    required = frozenset({"health", "agent_v2_sync_json", "agent_v2_sse"})
    if args.suite == "acceptance":
        required = required | frozenset({"agent_v2_fanout_probe", "agent_v2_malicious_deny"})
    sse_bad = _sse_missing_final(checks)

    e2e_retryable_provider_flakes_only = False
    if report_json_path and report_json_path.exists() and not args.skip_e2e:
        try:
            report_for_verdict = json.loads(report_json_path.read_text(encoding="utf-8"))
            e2e_retryable_provider_flakes_only = e2e_failures_are_retryable_provider_flakes(
                report_for_verdict
            )
        except (OSError, json.JSONDecodeError):
            e2e_retryable_provider_flakes_only = False

    verdict_obj = verdict_from_signals(
        checks_ok=chk_map,
        required_checks=required,
        e2e_ok=None if e2e is None else bool(e2e.get("ok")),
        metrics=metrics,
        sse_missing_final_in_checks=sse_bad,
        e2e_retryable_provider_flakes_only=(
            e2e is not None and not bool(e2e.get("ok")) and e2e_retryable_provider_flakes_only
        ),
        strict_subagent_lifecycle=bool(args.strict_v3_lifecycle),
        min_claim_verification_parse_rate=args.min_claim_verification_parse_rate,
    )

    review = TraceReviewV1(
        review_version=REVIEW_VERSION,
        generated_at=datetime.now(UTC).isoformat(),
        run_context=None,
        checks=tuple(check_from_dict(x) for x in checks),
        trace_timeline=trace_timeline,
        metrics=metrics,
        verdict=verdict_obj,
        e2e_audit=e2e,
        phoenix_snapshot_path=phoenix_snap_path,
    )

    review_dict = trace_review_to_dict(review)
    if args.with_long_thread_eval:

        def _long_thread() -> None:
            from chat_agent.long_thread_eval import (  # pylint: disable=import-outside-toplevel
                run_offline_long_thread_metrics,
            )

            lt_blob = run_offline_long_thread_metrics()
            mcur = dict(review_dict.get("metrics") or {})
            for k, v in (lt_blob.get("metrics") or {}).items():
                mcur[k] = v
            review_dict["metrics"] = mcur
            review_dict["long_thread_eval"] = lt_blob

        _execute_trace_stage(
            exec_stages,
            "long_thread_offline_eval",
            _long_thread,
            heartbeat_interval_s=hb_sec,
        )
    run_kind, graph_id = _runtime_attribution_from_env()
    if report_json_path and report_json_path.exists() and (run_kind is None or graph_id is None):
        try:
            report_obj = json.loads(report_json_path.read_text(encoding="utf-8"))
            cases = report_obj.get("cases") or []
            if isinstance(cases, list):
                for case in cases:
                    if not isinstance(case, dict):
                        continue
                    rm = case.get("run_metadata") or {}
                    if not isinstance(rm, dict):
                        continue
                    rk = str(rm.get("run_kind") or "").strip() or None
                    gid = str(rm.get("graph_id") or "").strip() or None
                    if rk is None or gid is None:
                        drk, dgid = _runtime_attribution_from_runtime_id(rm.get("agent_runtime"))
                        rk = rk or drk
                        gid = gid or dgid
                    if rk or gid:
                        run_kind = run_kind or rk
                        graph_id = graph_id or gid
                        break
        except (OSError, json.JSONDecodeError):
            pass
    server_rt = _server_agent_runtime_from_checks(checks)
    client_rt = (os.environ.get("SCIENCE_GRAPHRAG_AGENT_RUNTIME") or "").strip() or None
    merged_agent_runtime = client_rt or server_rt
    review_dict["run_context"] = {
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
        "feature_flags": {
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
            "long_thread_eval_offline": str(bool(args.with_long_thread_eval)).lower(),
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
        },
    }
    if phoenix_pull_meta:
        review_dict["phoenix_pull"] = phoenix_pull_meta

    if args.with_acceptance_summary:
        review_dict["acceptance_summary"] = build_acceptance_summary(review_dict)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(_json_safe_value(review_dict), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_markdown(args.out_md, review_dict)

    compaction_meta: dict[str, Any] | None = None
    merge_target = args.emit_merged_review or args.out_json
    if args.with_compaction_turns > 0:
        comp_json = args.out_json.parent / f"{args.out_json.stem}_compaction_review.json"
        compaction_meta = _execute_trace_stage(
            exec_stages,
            "compaction_turn_review",
            lambda: _run_compaction_turn_review(
                base_url=args.base_url,
                workspace_id=args.workspace_id,
                timeout=args.timeout,
                turns=args.with_compaction_turns,
                require_after=args.require_compaction_after,
                out_json=comp_json,
                emit_merged_into=merge_target,
                mode=str(args.compaction_mode),
                max_retries_per_turn=int(args.compaction_max_retries_per_turn),
                stage_heartbeat_cap_sec=hb_sec,
            ),
            heartbeat_interval_s=hb_sec,
        )
        if merge_target.exists():
            try:
                merged = json.loads(merge_target.read_text(encoding="utf-8"))
                merged["compaction_turn_review"] = compaction_meta
                _patch_run_context_execution_diagnostics(
                    merged,
                    exec_stages=exec_stages,
                    hb_sec=hb_sec,
                    e2e_subprocess_timeout_sec=e2e_subprocess_timeout_sec,
                )
                merge_target.write_text(
                    json.dumps(_json_safe_value(merged), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                review_dict = merged
                if args.with_acceptance_summary:
                    review_dict["acceptance_summary"] = build_acceptance_summary(review_dict)
                _write_markdown(args.out_md, review_dict)
            except (OSError, json.JSONDecodeError):
                review_dict["compaction_turn_review"] = compaction_meta
                _patch_run_context_execution_diagnostics(
                    review_dict,
                    exec_stages=exec_stages,
                    hb_sec=hb_sec,
                    e2e_subprocess_timeout_sec=e2e_subprocess_timeout_sec,
                )
                args.out_json.write_text(
                    json.dumps(_json_safe_value(review_dict), ensure_ascii=False, indent=2) + "\n"
                )
                if args.with_acceptance_summary:
                    review_dict["acceptance_summary"] = build_acceptance_summary(review_dict)
                _write_markdown(args.out_md, review_dict)

    if report_json_path:
        try:
            report_json_path.unlink(missing_ok=True)
        except OSError:
            pass

    print(f"[trace-review] json: {args.out_json}")
    print(f"[trace-review] md:   {args.out_md}")
    print(f"[trace-review] verdict: {review_dict['verdict']['status']}")
    status = str(review_dict["verdict"]["status"])
    return 0 if status != "fail" else 1


__all__ = ["run_agent_trace_review"]
