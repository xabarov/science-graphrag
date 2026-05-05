"""Tests for trace_timeline_from_case helper script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / "scripts" / "live_check" / "trace_timeline_from_case.py"


def test_trace_timeline_from_case_smoke(tmp_path: Path) -> None:
    case = {"cases": [{"case_id": "c1", "tool_trace": [{"tool": "final_answer", "ok": True}]}]}
    audit = {
        "cases": [
            {
                "trace_audit": {
                    "phoenix_structure_audit": {"coverage": {"covered": 2, "missing": []}},
                }
            }
        ]
    }
    cr = tmp_path / "case.json"
    ta = tmp_path / "audit.json"
    cr.write_text(json.dumps(case), encoding="utf-8")
    ta.write_text(json.dumps(audit), encoding="utf-8")
    out_j = tmp_path / "tl.json"
    out_m = tmp_path / "tl.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--case-result",
            str(cr),
            "--trace-audit",
            str(ta),
            "--out-json",
            str(out_j),
            "--out-md",
            str(out_m),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    payload = json.loads(out_j.read_text(encoding="utf-8"))
    assert payload["review_version"] == "trace-review-v1"
    assert len(payload["timeline"]) == 1
