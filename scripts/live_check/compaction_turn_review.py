#!/usr/bin/env python3
"""Review multi-turn compaction behavior for one thread."""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent

if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))


def _headers() -> dict[str, str]:
    out = {"Accept": "application/json"}
    auth = (os.environ.get("AGENT_LIVE_AUTHORIZATION") or "").strip()
    if auth:
        out["Authorization"] = auth
    admin = (os.environ.get("AGENT_LIVE_ADMIN_KEY") or "").strip()
    if admin:
        out["X-Admin-Key"] = admin
    return out


def _single_turn(
    client: httpx.Client,
    *,
    base_url: str,
    question: str,
    thread_id: str,
    workspace_id: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"question": question, "thread_id": thread_id}
    if workspace_id:
        payload["workspace_id"] = workspace_id
    res = client.post(f"{base_url}/v2/agent/query", json=payload, headers=_headers())
    res.raise_for_status()
    body = res.json()
    rm = body.get("run_metadata") if isinstance(body, dict) else {}
    comp = rm.get("compaction") if isinstance(rm, dict) else {}
    comp_audit = rm.get("compaction_audit") if isinstance(rm, dict) else {}
    llm_compact = comp_audit.get("llm_compact") if isinstance(comp_audit, dict) else {}
    side_ratio = (
        llm_compact.get("side_llm_cache_read_ratio") if isinstance(llm_compact, dict) else None
    )
    l4_skip_reason = (
        str(comp_audit.get("l4_skip_reason") or "").strip() if isinstance(comp_audit, dict) else ""
    ) or None
    paper_restored = (
        int(rm.get("post_compact_paper_sources_restored_count") or 0) if isinstance(rm, dict) else 0
    )
    return {
        "thread_id": body.get("thread_id"),
        "answer_class": body.get("answer_class"),
        "duration_ms": body.get("duration_ms"),
        "warnings": body.get("warnings"),
        "tool_trace_len": len(body.get("tool_trace") or []),
        "compaction": comp if isinstance(comp, dict) else {},
        "l4_skip_reason": l4_skip_reason,
        "side_llm_cache_read_ratio": side_ratio,
        "post_compact_paper_sources_restored_count": paper_restored,
    }


def _single_turn_with_wait_heartbeat(
    client: httpx.Client,
    *,
    base_url: str,
    question: str,
    thread_id: str,
    workspace_id: str | None,
    turn_idx: int,
    hb_sec: float,
) -> dict[str, Any]:
    """Run ``_single_turn`` while emitting stderr heartbeats during blocking HTTP wait."""
    done = threading.Event()
    t0 = time.perf_counter()

    def _hb_loop() -> None:
        while not done.wait(timeout=max(5.0, float(hb_sec))):
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            print(
                (
                    f"[compaction-review] turn_wait turn={turn_idx} thread_id={thread_id} "
                    f"elapsed_ms={elapsed_ms}"
                ),
                file=sys.stderr,
                flush=True,
            )

    hb_thread = threading.Thread(target=_hb_loop, name="compaction-review-hb", daemon=True)
    hb_thread.start()
    try:
        return _single_turn(
            client,
            base_url=base_url,
            question=question,
            thread_id=thread_id,
            workspace_id=workspace_id,
        )
    finally:
        done.set()


def _classify_turn_failure(
    *,
    mode: str,
    failure_kind_raw: str,
    turn_idx: int,
    elapsed_ms: int,
    silent_hang_threshold_s: float,
) -> tuple[str, str]:
    """Map transport failures to deterministic failure_kind/failure_reason."""
    if failure_kind_raw in {"http_read_timeout", "http_timeout"}:
        if mode == "focused_long_thread" and elapsed_ms >= int(silent_hang_threshold_s * 1000):
            return "silent_hang", f"silent_hang_turn_{turn_idx}"
        return "http_timeout", f"http_timeout_turn_{turn_idx}"
    if failure_kind_raw == "http_error":
        return "http_error", f"http_error_turn_{turn_idx}"
    return "unknown_error", f"unknown_error_turn_{turn_idx}"


def _write_md(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Compaction Turn Review",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Thread: `{report['thread_id']}`",
        f"- Turns: `{report['turns']}`",
        f"- Required compaction after turn: `{report['require_compaction_after']}`",
        f"- Mode: `{report.get('mode')}`",
        f"- Max retries per turn: `{report.get('max_retries_per_turn')}`",
        "",
        "## Turns",
        "",
        (
            "| Turn | attempt | tool_trace_len | compaction.kinds | side_ratio | "
            "paper_sources_restored | l4_skip_reason | warnings |"
        ),
        (
            "|------|---------|----------------|------------------|------------|"
            "-------------------------|----------------|----------|"
        ),
    ]
    for item in report["turn_reports"]:
        kinds = (item.get("compaction") or {}).get("kinds") or []
        l4_skip_reason = str(item.get("l4_skip_reason") or "")
        lines.append(
            (
                f"| {item['turn']} | {item.get('attempt', 1)} | {item.get('tool_trace_len')} | "
                f"`{','.join(kinds)}` | "
                f"`{item.get('side_llm_cache_read_ratio')}` | "
                f"`{item.get('post_compact_paper_sources_restored_count')}` | "
                f"`{l4_skip_reason}` | "
                f"`{','.join(item.get('warnings') or [])}` |"
            )
        )
    attempts = list(report.get("turn_attempts") or [])
    if attempts:
        lines.extend(
            [
                "",
                "## Turn attempts",
                "",
                "| Turn | attempt | ok | failure_kind | failure_reason | elapsed_ms |",
                "|------|---------|----|--------------|----------------|------------|",
            ]
        )
        for att in attempts:
            lines.append(
                (
                    f"| {att.get('turn')} | {att.get('attempt')} | `{att.get('ok')}` | "
                    f"`{att.get('failure_kind')}` | `{att.get('failure_reason')}` | "
                    f"`{att.get('elapsed_ms')}` |"
                )
            )
    lines.extend(["", "## Verdict", "", f"- Status: `{report['verdict']['status']}`"])
    if report.get("failure_reason"):
        lines.append(f"- Failure reason: `{report.get('failure_reason')}`")
    for reason in report["verdict"].get("reasons") or []:
        lines.append(f"- {reason}")
    if report.get("failed_turn") is not None:
        lines.append(f"- Failed turn: `{report.get('failed_turn')}`")
    if report.get("failure_kind"):
        lines.append(f"- Failure kind: `{report.get('failure_kind')}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    """Run N sync turns, collect compaction telemetry, and write JSON/MD verdict."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url", default=os.environ.get("AGENT_LIVE_BASE", "http://127.0.0.1:8000")
    )
    parser.add_argument(
        "--workspace-id", default=os.environ.get("AGENT_LIVE_WORKSPACE_ID", "").strip() or None
    )
    parser.add_argument("--turns", type=int, default=4)
    parser.add_argument("--require-compaction-after", type=int, default=2)
    parser.add_argument(
        "--timeout", type=float, default=float(os.environ.get("AGENT_LIVE_TIMEOUT_SEC", "240"))
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=_REPO_ROOT / "eval" / "results" / "compaction-turn-review.json",
    )
    parser.add_argument(
        "--out-md", type=Path, default=_REPO_ROOT / "eval" / "results" / "compaction-turn-review.md"
    )
    parser.add_argument(
        "--emit-merged-into",
        type=Path,
        default=None,
        help="Merge compaction_events into an existing trace-review-v1 JSON at this path",
    )
    parser.add_argument(
        "--heartbeat-sec",
        type=float,
        default=float(os.environ.get("AGENT_LIVE_COMPACTION_REVIEW_HEARTBEAT_SEC", "30")),
        help="Progress heartbeat interval for per-turn logs (minimum 5s)",
    )
    parser.add_argument(
        "--no-in-turn-heartbeat",
        action="store_true",
        help=(
            "Disable stderr heartbeats during blocking JSON /v2/agent/query wait " "(between turns)"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["default", "focused_long_thread"],
        default="default",
        help="Failure policy profile for multi-turn compaction review.",
    )
    parser.add_argument(
        "--max-retries-per-turn",
        type=int,
        default=int(os.environ.get("AGENT_LIVE_COMPACTION_RETRY_MAX", "0") or 0),
        help="Bounded retries for timeout-like failures (focused mode).",
    )
    parser.add_argument(
        "--retry-backoff-sec",
        type=float,
        default=float(os.environ.get("AGENT_LIVE_COMPACTION_RETRY_BACKOFF_SEC", "2.0")),
        help="Sleep between focused-mode retries (seconds).",
    )
    parser.add_argument(
        "--silent-hang-threshold-sec",
        type=float,
        default=float(os.environ.get("AGENT_LIVE_COMPACTION_SILENT_HANG_SEC", "180")),
        help="Timeout elapsed >= threshold is classified as silent_hang in focused mode.",
    )
    args = parser.parse_args()
    from dotenv_util import (  # pylint: disable=import-outside-toplevel,import-error
        resolve_live_base_url,
    )

    args.base_url = resolve_live_base_url(args.base_url)
    hb_sec = max(5.0, float(args.heartbeat_sec))
    in_turn_hb = not bool(args.no_in_turn_heartbeat)

    tid = f"compaction_review_{uuid.uuid4().hex[:12]}"
    timeout = httpx.Timeout(connect=20.0, read=args.timeout, write=120.0, pool=15.0)
    turn_reports: list[dict[str, Any]] = []
    turn_attempts: list[dict[str, Any]] = []
    failure_reason: str | None = None
    failure_kind: str | None = None
    failed_turn: int | None = None
    with httpx.Client(timeout=timeout) as client:
        for idx in range(1, args.turns + 1):
            q = f"Turn {idx}: summarize one sentence and include turn number."
            retries_left = max(0, int(args.max_retries_per_turn)) if args.mode == "focused_long_thread" else 0
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
                        item = _single_turn_with_wait_heartbeat(
                            client,
                            base_url=args.base_url.rstrip("/"),
                            question=q,
                            thread_id=tid,
                            workspace_id=args.workspace_id,
                            turn_idx=idx,
                            hb_sec=hb_sec,
                        )
                    else:
                        item = _single_turn(
                            client,
                            base_url=args.base_url.rstrip("/"),
                            question=q,
                            thread_id=tid,
                            workspace_id=args.workspace_id,
                        )
                except httpx.ReadTimeout:
                    elapsed_ms = int((time.perf_counter() - turn_t0) * 1000)
                    fk, fr = _classify_turn_failure(
                        mode=args.mode,
                        failure_kind_raw="http_read_timeout",
                        turn_idx=idx,
                        elapsed_ms=elapsed_ms,
                        silent_hang_threshold_s=float(args.silent_hang_threshold_sec),
                    )
                    turn_attempts.append(
                        {
                            "turn": idx,
                            "attempt": attempt,
                            "ok": False,
                            "failure_kind": fk,
                            "failure_reason": fr,
                            "elapsed_ms": elapsed_ms,
                        }
                    )
                    if retries_left > 0:
                        retries_left -= 1
                        attempt += 1
                        time.sleep(max(0.0, float(args.retry_backoff_sec)))
                        continue
                    failed_turn = idx
                    failure_kind = fk
                    failure_reason = fr
                    print(
                        f"[compaction-review] turn_fail turn={idx} reason={failure_reason} elapsed_ms={elapsed_ms}",
                        file=sys.stderr,
                        flush=True,
                    )
                    break
                except httpx.TimeoutException:
                    elapsed_ms = int((time.perf_counter() - turn_t0) * 1000)
                    fk, fr = _classify_turn_failure(
                        mode=args.mode,
                        failure_kind_raw="http_timeout",
                        turn_idx=idx,
                        elapsed_ms=elapsed_ms,
                        silent_hang_threshold_s=float(args.silent_hang_threshold_sec),
                    )
                    turn_attempts.append(
                        {
                            "turn": idx,
                            "attempt": attempt,
                            "ok": False,
                            "failure_kind": fk,
                            "failure_reason": fr,
                            "elapsed_ms": elapsed_ms,
                        }
                    )
                    if retries_left > 0:
                        retries_left -= 1
                        attempt += 1
                        time.sleep(max(0.0, float(args.retry_backoff_sec)))
                        continue
                    failed_turn = idx
                    failure_kind = fk
                    failure_reason = fr
                    print(
                        f"[compaction-review] turn_fail turn={idx} reason={failure_reason} elapsed_ms={elapsed_ms}",
                        file=sys.stderr,
                        flush=True,
                    )
                    break
                except httpx.HTTPError as exc:
                    elapsed_ms = int((time.perf_counter() - turn_t0) * 1000)
                    base_fr = f"http_error_turn_{idx}:{type(exc).__name__}"
                    turn_attempts.append(
                        {
                            "turn": idx,
                            "attempt": attempt,
                            "ok": False,
                            "failure_kind": "http_error",
                            "failure_reason": base_fr,
                            "elapsed_ms": elapsed_ms,
                        }
                    )
                    if retries_left > 0:
                        retries_left -= 1
                        attempt += 1
                        time.sleep(max(0.0, float(args.retry_backoff_sec)))
                        continue
                    failed_turn = idx
                    failure_kind = "http_error"
                    failure_reason = base_fr
                    print(
                        f"[compaction-review] turn_fail turn={idx} reason={failure_reason} elapsed_ms={elapsed_ms}",
                        file=sys.stderr,
                        flush=True,
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

    reasons: list[str] = []
    if failure_reason:
        reasons.append(failure_reason)
    for item in turn_reports:
        kinds = (item.get("compaction") or {}).get("kinds") or []
        if item["turn"] >= args.require_compaction_after and not kinds:
            reasons.append(f"missing_compaction_kinds_turn_{item['turn']}")
    verdict = {"status": "pass" if not reasons else "fail", "reasons": reasons}

    compaction_events: list[dict[str, Any]] = []
    for item in turn_reports:
        kinds = (item.get("compaction") or {}).get("kinds") or []
        if kinds:
            compaction_events.append(
                {
                    "type": "context_compacted",
                    "kinds": list(kinds),
                    "turn": item.get("turn"),
                    "thread_id": tid,
                    "side_llm_cache_read_ratio": item.get("side_llm_cache_read_ratio"),
                    "post_compact_paper_sources_restored_count": item.get(
                        "post_compact_paper_sources_restored_count"
                    ),
                }
            )

    report = {
        "review_version": "trace-review-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "thread_id": tid,
        "turns": args.turns,
        "require_compaction_after": args.require_compaction_after,
        "mode": args.mode,
        "max_retries_per_turn": int(args.max_retries_per_turn),
        "in_turn_heartbeat": in_turn_hb,
        "turn_attempts": turn_attempts,
        "turn_reports": turn_reports,
        "compaction_events": compaction_events,
        "failed_turn": failed_turn,
        "failure_kind": failure_kind,
        "failure_reason": failure_reason,
        "verdict": verdict,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_md(args.out_md, report)

    if args.emit_merged_into and args.emit_merged_into.exists():
        from trace_review_schema import (  # pylint: disable=import-outside-toplevel,import-error
            merge_compaction_into_review_dict,
        )

        merged_doc = json.loads(args.emit_merged_into.read_text(encoding="utf-8"))
        merged_out = merge_compaction_into_review_dict(merged_doc, compaction_events)
        args.emit_merged_into.write_text(
            json.dumps(merged_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"[compaction-review] merged into: {args.emit_merged_into}", flush=True)

    print(f"[compaction-review] json: {args.out_json}")
    print(f"[compaction-review] md:   {args.out_md}")
    return 0 if verdict["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
