"""Regression: judge prompt fingerprint must match frozen contract constant."""

from __future__ import annotations

from eval.agent_v3_quality.contract import EXPECTED_JUDGE_PROMPT_FINGERPRINT
from eval.agent_v3_quality.judge import judge_prompt_fingerprint


def test_judge_prompt_fingerprint_matches_contract() -> None:
    """When ``judge_prompt_v1.md`` changes, update ``EXPECTED_JUDGE_PROMPT_FINGERPRINT``."""

    assert judge_prompt_fingerprint() == EXPECTED_JUDGE_PROMPT_FINGERPRINT
