"""Execute multi-turn compaction review after CLI parsing."""

from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Protocol

import httpx

from .http_client import single_turn, single_turn_with_wait_heartbeat
from .report_builder import build_compaction_report_dict, write_compaction_markdown
from .retry_policy import classify_turn_failure, log_turn_fail_stderr


class CompactionParsedArgs(Protocol):  # pylint: disable=too-few-public-methods
    """CLI namespace shape after ``argparse`` (``compaction_turn_review`` entrypoint)."""

    base_url: str
    workspace_id: str | None
    turns: int
    require_compaction_after: int
    timeout: float
    out_json: Path
    out_md: Path
    emit_merged_into: Path | None
    heartbeat_sec: float | None
    no_in_turn_heartbeat: bool
    mode: str
    max_retries_per_turn: int
    retry_backoff_sec: float
    silent_hang_threshold_sec: float


def _transport_failure_kind_and_reason(
    exc: BaseException,
    *,
    mode: str,
    turn_idx: int,
    elapsed_ms: int,
    silent_hang_threshold_s: float,
) -> tuple[str, str]:
    """Map httpx errors to ``failure_kind`` / ``failure_reason``.

    ``ReadTimeout`` is checked before ``TimeoutException`` because it subclasses it.
    """
    if isinstance(exc, httpx.ReadTimeout):
        return classify_turn_failure(
            mode=mode,
            failure_kind_raw="http_read_timeout",
            turn_idx=turn_idx,
            elapsed_ms=elapsed_ms,
            silent_hang_threshold_s=silent_hang_threshold_s,
        )
    if isinstance(exc, httpx.TimeoutException):
        return classify_turn_failure(
            mode=mode,
            failure_kind_raw="http_timeout",
            turn_idx=turn_idx,
            elapsed_ms=elapsed_ms,
            silent_hang_threshold_s=silent_hang_threshold_s,
        )
    if isinstance(exc, httpx.HTTPError):
        return "http_error", f"http_error_turn_{turn_idx}:{type(exc).__name__}"
    raise TypeError(f"unexpected transport exception: {type(exc).__name__}")


def _append_failed_attempt(
    turn_attempts: list[dict[str, Any]],
    *,
    turn: int,
    attempt: int,
    failure_kind: str,
    failure_reason: str,
    elapsed_ms: int,
) -> None:
    turn_attempts.append(
        {
            "turn": turn,
            "attempt": attempt,
            "ok": False,
            "failure_kind": failure_kind,
            "failure_reason": failure_reason,
            "elapsed_ms": elapsed_ms,
        }
    )


def _run_client_turns(  # pylint: disable=too-many-locals
    client: httpx.Client,
    args: CompactionParsedArgs,
    *,
    tid: str,
    hb_sec: float,
    in_turn_hb: bool,
    mode_s: str,
    silent_thr: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None, str | None, int | None]:
    """Execute all turns; return reports, attempts, and optional hard-failure fields."""
    turn_reports: list[dict[str, Any]] = []
    turn_attempts: list[dict[str, Any]] = []
    failure_reason: str | None = None
    failure_kind: str | None = None
    failed_turn: int | None = None

    for idx in range(1, args.turns + 1):
        q = f"Turn {idx}: summarize one sentence and include turn number."
        retries_left = (
            max(0, int(args.max_retries_per_turn)) if args.mode == "focused_long_thread" else 0
        )
        attempt = 1
        item: dict[str, Any] | None = None
        while True:
            turn_t0 = time.perf_counter()
            print(
                (
                    f"[compaction-review] turn_start turn={idx} attempt={attempt} "
                    f"thread_id={tid} hb_sec={hb_sec} mode={args.mode}"
                ),
                file=sys.stderr,
                flush=True,
            )
            try:
                if in_turn_hb:
                    item = single_turn_with_wait_heartbeat(
                        client,
                        base_url=args.base_url.rstrip("/"),
                        question=q,
                        thread_id=tid,
                        workspace_id=args.workspace_id,
                        turn_idx=idx,
                        hb_sec=hb_sec,
                    )
                else:
                    item = single_turn(
                        client,
                        base_url=args.base_url.rstrip("/"),
                        question=q,
                        thread_id=tid,
                        workspace_id=args.workspace_id,
                    )
            except (httpx.ReadTimeout, httpx.TimeoutException, httpx.HTTPError) as exc:
                elapsed_ms = int((time.perf_counter() - turn_t0) * 1000)
                fk, fr = _transport_failure_kind_and_reason(
                    exc,
                    mode=mode_s,
                    turn_idx=idx,
                    elapsed_ms=elapsed_ms,
                    silent_hang_threshold_s=silent_thr,
                )
                _append_failed_attempt(
                    turn_attempts,
                    turn=idx,
                    attempt=attempt,
                    failure_kind=fk,
                    failure_reason=fr,
                    elapsed_ms=elapsed_ms,
                )
                if retries_left > 0:
                    retries_left -= 1
                    attempt += 1
                    time.sleep(max(0.0, float(args.retry_backoff_sec)))
                    continue
                failed_turn = idx
                failure_kind = fk
                failure_reason = fr
                log_turn_fail_stderr(
                    turn_idx=idx,
                    failure_reason=str(failure_reason or ""),
                    elapsed_ms=elapsed_ms,
                )
                break
            elapsed_ms = int((time.perf_counter() - turn_t0) * 1000)
            if item is None:
                break
            item["attempt"] = attempt
            comp_audit = (
                item.get("compaction", {}).get("audit")
                if isinstance(item.get("compaction"), dict)
                else None
            )
            if isinstance(comp_audit, dict):
                item["l4_skip_reason"] = comp_audit.get("l4_skip_reason")
            turn_attempts.append(
                {
                    "turn": idx,
                    "attempt": attempt,
                    "ok": True,
                    "failure_kind": None,
                    "failure_reason": None,
                    "elapsed_ms": elapsed_ms,
                }
            )
            break
        if item is None:
            break
        item["turn"] = idx
        turn_reports.append(item)
        kinds = (item.get("compaction") or {}).get("kinds") or []
        print(
            (
                f"[compaction-review] turn_done turn={idx} elapsed_ms={elapsed_ms} "
                f"kinds={','.join(str(k) for k in kinds)} "
                f"side_ratio={item.get('side_llm_cache_read_ratio')!r} "
                f"paper_restored={item.get('post_compact_paper_sources_restored_count')!r}"
            ),
            file=sys.stderr,
            flush=True,
        )
        if failure_reason:
            break

    return turn_reports, turn_attempts, failure_reason, failure_kind, failed_turn


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
        turn_reports, turn_attempts, failure_reason, failure_kind, failed_turn = _run_client_turns(
            client,
            args,
            tid=tid,
            hb_sec=hb_sec,
            in_turn_hb=in_turn_hb,
            mode_s=mode_s,
            silent_thr=silent_thr,
        )

    reasons: list[str] = []
    if failure_reason:
        reasons.append(failure_reason)
    for report_item in turn_reports:
        kinds = (report_item.get("compaction") or {}).get("kinds") or []
        if report_item["turn"] >= args.require_compaction_after and not kinds:
            reasons.append(f"missing_compaction_kinds_turn_{report_item['turn']}")
    verdict = {"status": "pass" if not reasons else "fail", "reasons": reasons}

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

        merged_doc = json.loads(emit_merged.read_text(encoding="utf-8"))
        merged_out = merge_compaction_into_review_dict(merged_doc, report["compaction_events"])
        emit_merged.write_text(
            json.dumps(merged_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"[compaction-review] merged into: {emit_merged}", flush=True)

    print(f"[compaction-review] json: {args.out_json}")
    print(f"[compaction-review] md:   {args.out_md}")
    return 0 if verdict["status"] == "pass" else 1


__all__ = ["CompactionParsedArgs", "run_compaction_review_from_parsed_args"]
