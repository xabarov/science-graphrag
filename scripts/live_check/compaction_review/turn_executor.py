"""HTTP turn execution with retries for compaction review."""

from __future__ import annotations

import time
from typing import Any

import httpx

from .heartbeat_monitor import log_turn_done, log_turn_start
from .http_client import single_turn, single_turn_with_wait_heartbeat
from .parsed_args import CompactionParsedArgs
from .retry_policy import classify_turn_failure, log_turn_fail_stderr


def transport_failure_kind_and_reason(
    exc: BaseException,
    *,
    mode: str,
    turn_idx: int,
    elapsed_ms: int,
    silent_hang_threshold_s: float,
) -> tuple[str, str]:
    """Map httpx errors to ``failure_kind`` / ``failure_reason``."""
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


def append_failed_attempt(
    turn_attempts: list[dict[str, Any]],
    *,
    turn: int,
    attempt: int,
    failure_kind: str,
    failure_reason: str,
    elapsed_ms: int,
) -> None:
    """Record a failed HTTP attempt."""
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


def execute_compaction_turns(  # pylint: disable=too-many-locals
    client: httpx.Client,
    args: CompactionParsedArgs,
    *,
    thread_id: str,
    hb_sec: float,
    in_turn_hb: bool,
    mode_s: str,
    silent_thr: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None, str | None, int | None]:
    """Run all turns; return ``turn_reports``, ``turn_attempts``, and optional hard-failure fields."""
    turn_reports: list[dict[str, Any]] = []
    turn_attempts: list[dict[str, Any]] = []
    failure_reason: str | None = None
    failure_kind: str | None = None
    failed_turn: int | None = None

    for idx in range(1, args.turns + 1):
        q = f"Turn {idx}: summarize one sentence and include turn number."
        is_focused = args.mode == "focused_long_thread"
        retries_left = max(0, int(args.max_retries_per_turn)) if is_focused else 0
        attempt = 1
        item: dict[str, Any] | None = None
        while True:
            turn_t0 = time.perf_counter()
            log_turn_start(
                turn_idx=idx,
                attempt=attempt,
                thread_id=thread_id,
                hb_sec=hb_sec,
                mode=str(args.mode),
            )
            try:
                if in_turn_hb:
                    item = single_turn_with_wait_heartbeat(
                        client,
                        base_url=args.base_url.rstrip("/"),
                        question=q,
                        thread_id=thread_id,
                        workspace_id=args.workspace_id,
                        turn_idx=idx,
                        hb_sec=hb_sec,
                    )
                else:
                    item = single_turn(
                        client,
                        base_url=args.base_url.rstrip("/"),
                        question=q,
                        thread_id=thread_id,
                        workspace_id=args.workspace_id,
                    )
            except (httpx.ReadTimeout, httpx.TimeoutException, httpx.HTTPError) as exc:
                elapsed_ms = int((time.perf_counter() - turn_t0) * 1000)
                fk, fr = transport_failure_kind_and_reason(
                    exc,
                    mode=mode_s,
                    turn_idx=idx,
                    elapsed_ms=elapsed_ms,
                    silent_hang_threshold_s=silent_thr,
                )
                append_failed_attempt(
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
        log_turn_done(
            turn_idx=idx,
            elapsed_ms=elapsed_ms,
            kinds=kinds,
            side_ratio=item.get("side_llm_cache_read_ratio"),
            paper_restored=item.get("post_compact_paper_sources_restored_count"),
        )
        if failure_reason:
            break

    return turn_reports, turn_attempts, failure_reason, failure_kind, failed_turn


__all__ = [
    "append_failed_attempt",
    "execute_compaction_turns",
    "transport_failure_kind_and_reason",
]
