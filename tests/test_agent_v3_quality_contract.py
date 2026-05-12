"""Contract helpers for agent_v3_quality benchmark."""

from __future__ import annotations

from eval.agent_v3_quality.contract import resolve_benchmark_judge_model


def test_resolve_benchmark_judge_model_prefers_explicit() -> None:
    out = resolve_benchmark_judge_model(
        judge_model="openai/gpt-4o",
        judge_model_family="anthropic",
    )
    assert out == "openai/gpt-4o"


def test_resolve_benchmark_judge_model_reads_family_env(monkeypatch) -> None:
    monkeypatch.setenv(
        "SCIENCE_GRAPHRAG_AGENT_V3_QUALITY_JUDGE_MODEL_ANTHROPIC",
        "anthropic/claude-sonnet-4.6",
    )
    out = resolve_benchmark_judge_model(
        judge_model=None,
        judge_model_family="anthropic",
    )
    assert out == "anthropic/claude-sonnet-4.6"


def test_resolve_benchmark_judge_model_uses_default_family() -> None:
    out = resolve_benchmark_judge_model(
        judge_model=None,
        judge_model_family="openai",
    )
    assert out == "openai/gpt-4o-mini"
