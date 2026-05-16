#!/usr/bin/env python3
"""Live smoke: external web research quality gates via POST /v2/agent/query.

Validates official-source pass, source diversity signals, and negative-claim guard
for product/version internet research (YOLO11 regression lane).

Environment::

    AGENT_LIVE_BASE              API root (default http://127.0.0.1:18787)
    AGENT_LIVE_WORKSPACE_ID      workspace UUID (recommended: ws-pilot-od)
    AGENT_LIVE_TIMEOUT_SEC       per-request timeout (default 300)
    PHOENIX_UI_BASE_URL          optional; pull spans when phoenix_trace_id present

Usage::

    export AGENT_LIVE_BASE=http://127.0.0.1:18787
    export AGENT_LIVE_WORKSPACE_ID=ws-pilot-od
    .venv/bin/python scripts/live_check/external_web_research_smoke.py
    .venv/bin/python scripts/live_check/external_web_research_smoke.py --write-json eval/results/external-web-research-smoke.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from external_web_research_validate import (  # noqa: E402
    evaluate_external_web_research_case,
    phoenix_has_official_lookup_span,
)
from http_suite_core import _extra_headers  # noqa: E402

_DEFAULT_QUESTION = "поищи в интернете о YOLO v 11 \nЧто по ней известно?"


def _maybe_pull_phoenix(trace_id: str | None, *, timeout: float) -> dict[str, Any] | None:
    tid = str(trace_id or "").strip()
    if not tid:
        return None
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    from eval.chat_agent.phoenix_export import extract_span_names_for_trace, try_fetch_phoenix_spans

    snap = try_fetch_phoenix_spans(tid, timeout_s=min(30.0, timeout))
    names: list[str] = []
    if snap.get("ok") and snap.get("payload") is not None:
        norm = str(snap.get("trace_id") or tid).replace("-", "").lower()
        names = extract_span_names_for_trace(snap["payload"], norm)
    return {
        "fetch_ok": bool(snap.get("ok")),
        "span_count": len(names),
        "official_web_lookup_span": phoenix_has_official_lookup_span(names),
        "span_names_sample": names[:40],
        "error": snap.get("error"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("AGENT_LIVE_BASE", "http://127.0.0.1:18787"),
    )
    parser.add_argument(
        "--workspace-id",
        default=os.environ.get("AGENT_LIVE_WORKSPACE_ID", "").strip() or None,
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("AGENT_LIVE_TIMEOUT_SEC", "300")),
    )
    parser.add_argument("--question", default=_DEFAULT_QUESTION)
    parser.add_argument("--write-json", type=Path, default=None)
    parser.add_argument("--skip-phoenix", action="store_true")
    args = parser.parse_args()

    base = str(args.base_url).rstrip("/")
    payload: dict[str, Any] = {
        "question": args.question,
        "web_research_enabled": True,
    }
    if args.workspace_id:
        payload["workspace_id"] = args.workspace_id

    report: dict[str, Any] = {
        "base_url": base,
        "workspace_id": args.workspace_id,
        "question": args.question,
    }
    try:
        with httpx.Client(timeout=args.timeout) as client:
            r = client.post(
                f"{base}/v2/agent/query",
                json=payload,
                headers={"Accept": "application/json", **_extra_headers()},
            )
            r.raise_for_status()
            data = r.json()
    except Exception as exc:  # noqa: BLE001
        report["ok"] = False
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if args.write_json:
            args.write_json.parent.mkdir(parents=True, exist_ok=True)
            args.write_json.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return 1

    verdict = evaluate_external_web_research_case(data if isinstance(data, dict) else {})
    report.update(verdict)
    report["http_ok"] = True

    if not args.skip_phoenix:
        phoenix = _maybe_pull_phoenix(
            str(data.get("phoenix_trace_id") or "") if isinstance(data, dict) else None,
            timeout=args.timeout,
        )
        if phoenix is not None:
            report["phoenix"] = phoenix

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
