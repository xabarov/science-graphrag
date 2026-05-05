#!/usr/bin/env python3
"""Fetch Phoenix traces into JSONL snapshots for offline review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from eval.chat_agent.phoenix_export import (  # pylint: disable=wrong-import-position
    extract_span_names_for_trace,
    try_fetch_phoenix_spans,
)


def _iter_trace_ids(args: argparse.Namespace) -> list[str]:
    out = [x.strip() for x in (args.trace_id or []) if str(x).strip()]
    if args.trace_id_file:
        for line in args.trace_id_file.read_text(encoding="utf-8").splitlines():
            tid = line.strip()
            if tid:
                out.append(tid)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-id", action="append", default=[])
    parser.add_argument("--trace-id-file", type=Path)
    parser.add_argument("--base-url", default=None, help="Phoenix UI base URL")
    parser.add_argument("--project-id", default=None, help="Phoenix project id/name")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--out-jsonl", type=Path, required=True)
    args = parser.parse_args()

    trace_ids = _iter_trace_ids(args)
    if not trace_ids:
        raise SystemExit("Provide at least one --trace-id or --trace-id-file.")

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as fh:
        for tid in trace_ids:
            snap = try_fetch_phoenix_spans(
                tid,
                base_url=args.base_url,
                timeout_s=args.timeout,
                project_identifier=args.project_id,
            )
            names = []
            payload = snap.get("payload")
            norm_tid = str(snap.get("trace_id") or tid).replace("-", "").lower()
            if snap.get("ok") and payload is not None:
                names = extract_span_names_for_trace(payload, norm_tid)
            row = {
                "trace_id": tid,
                "fetch_ok": bool(snap.get("ok")),
                "payload_kind": snap.get("payload_kind"),
                "error": snap.get("error"),
                "span_count": len(names),
                "span_names": names,
                "source_url": snap.get("url"),
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[phoenix-trace-pull] wrote {len(trace_ids)} traces to {args.out_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
