"""Unit tests for retry logic in agent_od_workspace_e2e_audit."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts" / "live_check"

if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import agent_od_workspace_e2e_audit as audit_mod  # pylint: disable=import-error


def test_case_acceptance_passes_when_final_answer_present() -> None:
    case = {
        "http_ok": True,
        "final_answer_reached": True,
        "answer_len": 120,
    }
    assert audit_mod._case_passes_acceptance(case) is True


def test_should_retry_after_deadline_warning() -> None:
    case = {
        "warnings": ["agent_turn_deadline_exceeded"],
        "notes": ["last_tool_not_final_answer"],
        "run_metadata": {"agent_turn_deadline_exceeded": True},
    }
    assert audit_mod._should_retry_after_case_failure(case) is True


def test_should_not_retry_for_regular_logic_failure() -> None:
    case = {
        "warnings": ["no_workspace"],
        "notes": ["last_tool_not_final_answer"],
        "run_metadata": {},
    }
    assert audit_mod._should_retry_after_case_failure(case) is False
