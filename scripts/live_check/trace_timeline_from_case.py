#!/usr/bin/env python3
"""Build a unified timeline from case_result and trace_audit artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_tool_steps(case: dict[str, Any]) -> list[dict[str, Any]]:
    trace = case.get("tool_trace") or []
    steps: list[dict[str, Any]] = []
    for idx, item in enumerate(trace, start=1):
        if not isinstance(item, dict):
            continue
        steps.append(
            {
                "idx": idx,
                "tool": item.get("tool"),
                "ok": bool(item.get("ok", True)),
                "duration_ms": item.get("duration_ms"),
                "error": item.get("error"),
            }
        )
    return steps


def _timeline(case: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    phoenix = audit.get("phoenix_structure_audit") if isinstance(audit, dict) else None
    coverage = (phoenix or {}).get("coverage") if isinstance(phoenix, dict) else {}
    return {
        "case_id": case.get("case_id") or case.get("name") or "unknown",
        "thread_id": case.get("thread_id"),
        "tool_steps": _extract_tool_steps(case),
        "phoenix_alignment": {
            "covered": (coverage or {}).get("covered"),
            "missing": (coverage or {}).get("missing") or [],
        },
        "warnings": case.get("warnings") or [],
        "fail_reasons": audit.get("fail_reasons") or [],
    }


def _write_md(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Trace Timeline",
        "",
        "| Case | Tool steps | Phoenix covered | Missing spans |",
        "|------|------------|-----------------|---------------|",
    ]
    for item in payload.get("timeline") or []:
        lines.append(
            f"| `{item.get('case_id')}` | {len(item.get('tool_steps') or [])} | "
            f"{item.get('phoenix_alignment', {}).get('covered')} | "
            f"{len(item.get('phoenix_alignment', {}).get('missing') or [])} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-result", type=Path, required=True)
    parser.add_argument("--trace-audit", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()

    case = _load_json(args.case_result)
    audit = _load_json(args.trace_audit)
    if isinstance(case, dict) and "cases" in case and isinstance(case["cases"], list):
        case_items = [x for x in case["cases"] if isinstance(x, dict)]
    else:
        case_items = [case]
    if isinstance(audit, dict) and "cases" in audit and isinstance(audit["cases"], list):
        audit_items = [x for x in audit["cases"] if isinstance(x, dict)]
    else:
        audit_items = [audit]
    timeline = []
    for idx, case_item in enumerate(case_items):
        aud_item = audit_items[idx] if idx < len(audit_items) else {}
        timeline.append(_timeline(case_item, aud_item))

    payload = {"review_version": "trace-review-v1", "timeline": timeline}
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_md(args.out_md, payload)
    print(f"[trace-timeline] json: {args.out_json}")
    print(f"[trace-timeline] md:   {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
