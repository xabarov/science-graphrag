#!/usr/bin/env python3
"""Review multi-turn compaction behavior for one thread."""

from __future__ import annotations

import argparse
import json
import os
import sys
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
    return {
        "thread_id": body.get("thread_id"),
        "answer_class": body.get("answer_class"),
        "duration_ms": body.get("duration_ms"),
        "warnings": body.get("warnings"),
        "tool_trace_len": len(body.get("tool_trace") or []),
        "compaction": comp if isinstance(comp, dict) else {},
    }


def _write_md(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Compaction Turn Review",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Thread: `{report['thread_id']}`",
        f"- Turns: `{report['turns']}`",
        f"- Required compaction after turn: `{report['require_compaction_after']}`",
        "",
        "## Turns",
        "",
        "| Turn | tool_trace_len | compaction.kinds | warnings |",
        "|------|----------------|------------------|----------|",
    ]
    for item in report["turn_reports"]:
        kinds = (item.get("compaction") or {}).get("kinds") or []
        lines.append(
            f"| {item['turn']} | {item.get('tool_trace_len')} | `{','.join(kinds)}` | `{','.join(item.get('warnings') or [])}` |"
        )
    lines.extend(["", "## Verdict", "", f"- Status: `{report['verdict']['status']}`"])
    for reason in report["verdict"].get("reasons") or []:
        lines.append(f"- {reason}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
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
    args = parser.parse_args()

    tid = f"compaction_review_{uuid.uuid4().hex[:12]}"
    timeout = httpx.Timeout(connect=20.0, read=args.timeout, write=120.0, pool=15.0)
    turn_reports: list[dict[str, Any]] = []
    with httpx.Client(timeout=timeout) as client:
        for idx in range(1, args.turns + 1):
            q = f"Turn {idx}: summarize one sentence and include turn number."
            item = _single_turn(
                client,
                base_url=args.base_url.rstrip("/"),
                question=q,
                thread_id=tid,
                workspace_id=args.workspace_id,
            )
            item["turn"] = idx
            turn_reports.append(item)

    reasons: list[str] = []
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
                }
            )

    report = {
        "review_version": "trace-review-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "thread_id": tid,
        "turns": args.turns,
        "require_compaction_after": args.require_compaction_after,
        "turn_reports": turn_reports,
        "compaction_events": compaction_events,
        "verdict": verdict,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_md(args.out_md, report)

    if args.emit_merged_into and args.emit_merged_into.exists():
        from trace_review_schema import (  # pylint: disable=import-outside-toplevel
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
