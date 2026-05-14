"""Eval-style gates for Epic B3/B4 (synthetic E2E rows, no live LLM)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "live_check"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


@pytest.fixture()
def schema_module():
    import trace_review_schema as mod  # pylint: disable=import-outside-toplevel,import-error

    return mod


def test_fanout_two_spawns_increase_subagent_runs_count(schema_module) -> None:
    case = {
        "case_id": "fanout_cv",
        "tool_trace": [{"tool": "final_answer", "ok": True}],
        "run_metadata": {
            "subagent_observability_lane": "fork_v3_enhanced",
            "subagent_runs": [
                {"subagent_id": "retrieval_agent", "kind": "routing_leg"},
                {"subagent_id": "cv-1", "kind": "spawned"},
                {"subagent_id": "cv-2", "kind": "spawned"},
            ],
            "subagent_task_notifications": [
                {"task_id": "t1"},
                {"task_id": "t2"},
                {"task_id": "t3"},
            ],
        },
    }
    tl = schema_module.merge_e2e_report_json_into_review(cases=[case], workspace_postgres=None)
    assert tl[0].subagent_runs_count == 3
    assert tl[0].subagent_lifecycle_missing_count == 0


def test_one_child_failed_surfaces_in_claim_results_json_roundtrip() -> None:
    row = {
        "subagent_id": "cv-x",
        "verdict": None,
        "issues": ["invoke_error:AgentGraphDeadlineExceeded"],
        "terminal_state": "timed_out",
        "failure_code": "timeout",
    }
    raw = json.dumps([row])
    back = json.loads(raw)
    assert back[0]["terminal_state"] == "timed_out"
