"""P2: sidechain JSONL path contract (no graph invoke)."""

from __future__ import annotations

from pathlib import Path

from science_graphrag.agent.tool_execution_pipeline import _sidechain_jsonl_path
from science_graphrag.config import Settings


def test_sidechain_jsonl_path_under_configured_dir() -> None:
    settings = Settings.model_construct(agent_sidechain_transcripts_dir=".agent_sidechains_test")
    p = _sidechain_jsonl_path(settings, "retrieval_agent:tag1")
    assert p == Path(".agent_sidechains_test") / "retrieval_agent:tag1.jsonl"
