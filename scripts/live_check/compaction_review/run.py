"""Execute multi-turn compaction review after CLI parsing."""

from __future__ import annotations

import json
import sys
import uuid

import httpx

from .parsed_args import CompactionParsedArgs
from .report_builder import build_compaction_report_dict, write_compaction_markdown
from .result_aggregator import build_compaction_verdict
from .turn_executor import execute_compaction_turns


def run_compaction_review_from_parsed_args(  # pylint: disable=too-many-locals
    args: CompactionParsedArgs,
) -> int:
    """Run N sync turns, collect compaction telemetry, and write JSON/MD verdict."""
    if args.heartbeat_sec is None:
        from trace_review.orchestrator_env import (  # pylint: disable=import-outside-toplevel
            compaction_in_turn_heartbeat_sec,
        )

        args.heartbeat_sec = compaction_in_turn_heartbeat_sec(mode=str(args.mode))
    hb_sec = max(5.0, float(args.heartbeat_sec))
    in_turn_hb = not bool(args.no_in_turn_heartbeat)

    tid = f"compaction_review_{uuid.uuid4().hex[:12]}"
    timeout = httpx.Timeout(connect=20.0, read=args.timeout, write=120.0, pool=15.0)
    mode_s = str(args.mode)
    silent_thr = float(args.silent_hang_threshold_sec)
    with httpx.Client(timeout=timeout) as client:
        turn_reports, turn_attempts, failure_reason, failure_kind, failed_turn = (
            execute_compaction_turns(
                client,
                args,
                thread_id=tid,
                hb_sec=hb_sec,
                in_turn_hb=in_turn_hb,
                mode_s=mode_s,
                silent_thr=silent_thr,
            )
        )

    verdict = build_compaction_verdict(
        failure_reason=failure_reason,
        turn_reports=turn_reports,
        require_compaction_after=args.require_compaction_after,
    )

    report = build_compaction_report_dict(
        thread_id=tid,
        turns=args.turns,
        require_compaction_after=args.require_compaction_after,
        mode=mode_s,
        max_retries_per_turn=int(args.max_retries_per_turn),
        hb_sec=hb_sec,
        in_turn_hb=in_turn_hb,
        silent_hang_threshold_sec=silent_thr,
        turn_reports=turn_reports,
        turn_attempts=turn_attempts,
        failure_reason=failure_reason,
        failure_kind=failure_kind,
        failed_turn=failed_turn,
        verdict=verdict,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_compaction_markdown(args.out_md, report)

    emit_merged = args.emit_merged_into
    if emit_merged is not None and emit_merged.exists():
        from trace_review_schema import (  # pylint: disable=import-outside-toplevel,import-error
            merge_compaction_into_review_dict,
        )

        try:
            merged_doc = json.loads(emit_merged.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(
                f"[compaction-review] merge failed: cannot read/parse {emit_merged}: {exc}",
                file=sys.stderr,
                flush=True,
            )
            return 1
        try:
            merged_out = merge_compaction_into_review_dict(merged_doc, report["compaction_events"])
            emit_merged.write_text(
                json.dumps(merged_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        except (OSError, TypeError, ValueError, KeyError) as exc:
            print(
                f"[compaction-review] merge failed writing {emit_merged}: {exc}",
                file=sys.stderr,
                flush=True,
            )
            return 1
        print(f"[compaction-review] merged into: {emit_merged}", flush=True)

    print(f"[compaction-review] json: {args.out_json}")
    print(f"[compaction-review] md:   {args.out_md}")
    return 0 if verdict["status"] == "pass" else 1


__all__ = ["CompactionParsedArgs", "run_compaction_review_from_parsed_args"]
