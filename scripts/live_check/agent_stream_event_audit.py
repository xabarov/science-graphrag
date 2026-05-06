#!/usr/bin/env python3
"""Audit agent SSE event classes from trace-review e2e JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _iter_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.is_file():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            events.append(row)
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in-jsonl", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    args = parser.parse_args()

    events = _iter_events(args.in_jsonl)
    total_error = 0
    non_internal = 0
    using_tool_count = 0
    for ev in events:
        event_type = str(ev.get("type") or "")
        if event_type == "error":
            total_error += 1
            err_cls = str(ev.get("error_class") or "")
            if err_cls and err_cls != "internal_error":
                non_internal += 1
        if event_type == "product_step" and str(ev.get("code") or "") == "using_tool":
            using_tool_count += 1

    payload = {
        "source": str(args.in_jsonl),
        "total_events": len(events),
        "error_total": total_error,
        "error_non_internal_total": non_internal,
        "error_non_internal_share": (non_internal / total_error) if total_error else None,
        "product_step_using_tool_total": using_tool_count,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
