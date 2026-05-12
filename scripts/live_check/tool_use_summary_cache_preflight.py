#!/usr/bin/env python3
"""Optional live pre-flight for Wave E2 ``tool_use_summary`` prompt-cache (PR2).

Without ``--live``: prints canonical JSON self-check (no API).

With ``--live``: runs ``summarize_tool_result_payload_dict`` N times on the same
payload and prints ``side_llm_cache_read_ratio`` from metadata. Requires valid
``Settings`` / extraction LLM (see ``long-running-ops.mdc``).

Example::

  .venv/bin/python scripts/live_check/tool_use_summary_cache_preflight.py --repeat 5 --live
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _large_payload() -> dict:
    rows = [{"work_id": f"w{i % 200}", "title": f"Paper {i}"} for i in range(400)]
    return {"ok": True, "row_count": len(rows), "rows": rows, "workspace_id": "ws_preflight"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repeat", type=int, default=5, help="Number of identical summarize calls."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call real side-LLM (requires API keys in Settings).",
    )
    args = parser.parse_args()

    from science_graphrag.agent.tool_use_summary import (
        canonical_tool_json_for_side_llm,
        summarize_tool_result_payload_dict,
    )

    p1 = {"z": 1, "a": 2}
    p2 = {"a": 2, "z": 1}
    if canonical_tool_json_for_side_llm(p1) != canonical_tool_json_for_side_llm(p2):
        print("FAIL: canonical JSON not stable across key order", file=sys.stderr)
        return 1
    print("OK: canonical JSON stable (no API)")

    if not args.live:
        print("Skip live calls (pass --live after pre-flight checklist).")
        return 0

    from science_graphrag.config import Settings

    settings = Settings()
    if not (settings.extraction_llm_api_key or "").strip():
        print("ERROR: extraction_llm_api_key empty; refuse live preflight.", file=sys.stderr)
        return 2

    payload = _large_payload()
    raw = json.dumps(payload, ensure_ascii=True, default=str)
    if len(raw) < int(getattr(settings, "agent_tool_use_summary_min_payload_chars", 6000) or 6000):
        print("ERROR: fixture too small for tool_use_summary threshold", file=sys.stderr)
        return 3

    ratios: list[float] = []
    for i in range(max(1, args.repeat)):
        _merged, meta = summarize_tool_result_payload_dict(
            settings=settings,
            tool_name="find_works",
            payload=payload,
        )
        r = meta.get("side_llm_cache_read_ratio")
        if isinstance(r, (int, float)):
            ratios.append(float(r))
        print(f"run {i + 1}: side_llm_cache_read_ratio={r!r} forked={meta.get('forked')!r}")

    if ratios:
        print(f"mean_ratio={statistics.mean(ratios):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
