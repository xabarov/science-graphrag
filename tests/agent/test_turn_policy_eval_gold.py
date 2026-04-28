"""Load eval/chat_agent gold JSON and assert rules_v0 TurnPolicy expectations."""

from __future__ import annotations

import json
from pathlib import Path

from science_graphrag.agent.coordination.turn_policy import classify_turn_policy

_GOLD = (
    Path(__file__).resolve().parents[2]
    / "eval"
    / "chat_agent"
    / "coordinator_turn_policy_gold.json"
)


def test_coordinator_turn_policy_gold_json_cases() -> None:
    data = json.loads(_GOLD.read_text(encoding="utf-8"))
    for case in data["cases"]:
        q = str(case["question"])
        ws = case.get("workspace_id")
        p = classify_turn_policy(question=q, workspace_id=ws)
        assert p.tool_policy == case["expect_tool_policy"], case["id"]
        assert p.conversation_intent == case["expect_intent"], case["id"]
