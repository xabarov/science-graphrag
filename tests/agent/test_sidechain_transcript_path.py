"""P2: sidechain JSONL path contract (no graph invoke)."""

from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock

from science_graphrag.agent.sidechain_paths import (
    _fallback_sidechain_dir,
    sidechain_transcripts_root,
)
from science_graphrag.agent.tool_execution_pipeline import _sidechain_jsonl_path
from science_graphrag.agent.subagents.sidechain_transcript import append_subagent_sidechain_event
from science_graphrag.config import Settings


def test_sidechain_jsonl_path_under_configured_dir() -> None:
    settings = Settings.model_construct(agent_sidechain_transcripts_dir=".agent_sidechains_test")
    p = _sidechain_jsonl_path(settings, "retrieval_agent:tag1")
    assert p == Path(".agent_sidechains_test") / "retrieval_agent:tag1.jsonl"


def test_sidechain_jsonl_path_falls_back_for_mocked_settings() -> None:
    settings = MagicMock()
    settings.agent_sidechain_transcripts_dir = MagicMock()
    p = _sidechain_jsonl_path(settings, "retrieval_agent:tag1")
    assert p == _fallback_sidechain_dir() / "retrieval_agent:tag1.jsonl"


def test_append_subagent_sidechain_event_ignores_truthy_mock_flag(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    settings = MagicMock()
    settings.agent_sidechain_transcripts_enabled = MagicMock()
    settings.agent_sidechain_transcripts_dir = MagicMock()
    out = append_subagent_sidechain_event(
        settings,
        parent_turn_id="parent-1",
        subagent_id="child-1",
        event={"type": "routing_leg_started"},
    )
    assert out is None
    assert list(tmp_path.iterdir()) == []


def test_sidechain_root_falls_back_when_default_dir_unwritable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    blocked = tmp_path / ".agent_sidechains"
    blocked.mkdir()
    blocked.chmod(0o555)
    settings = Settings.model_construct(agent_sidechain_transcripts_dir=".agent_sidechains")
    root = sidechain_transcripts_root(settings)
    assert root == home / ".scigraph" / "agent_sidechains"


def test_sidechain_root_keeps_explicit_custom_dir_even_if_unwritable(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    custom = tmp_path / "custom_sidechains"
    custom.mkdir()
    custom.chmod(0o555)
    settings = Settings.model_construct(agent_sidechain_transcripts_dir=str(custom))
    root = sidechain_transcripts_root(settings)
    assert root == custom
