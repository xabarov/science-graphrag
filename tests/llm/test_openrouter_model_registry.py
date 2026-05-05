"""Tests for curated OpenRouter model registry."""

from __future__ import annotations

from science_graphrag.llm import openrouter_model_registry as reg


def test_popular_models_have_profiles() -> None:
    missing = [
        mid
        for mid in reg.OPENROUTER_POPULAR_MODEL_IDS
        if reg.get_openrouter_model_profile(mid) is None
    ]
    assert not missing


def test_gpt4o_prefers_structured_outputs() -> None:
    assert reg.openrouter_auto_uses_instructor_structured_outputs(
        base_url="https://openrouter.ai/api/v1",
        model_id="openai/gpt-4o",
    )


def test_claude_sonnet4_sticks_to_tools_compatible_path() -> None:
    prof = reg.get_openrouter_model_profile("anthropic/claude-sonnet-4")
    assert prof is not None
    assert not prof.openrouter_structured_outputs
    assert not reg.openrouter_auto_uses_instructor_structured_outputs(
        base_url="https://openrouter.ai/api/v1",
        model_id="anthropic/claude-sonnet-4",
    )


def test_claude_sonnet_46_uses_structured_outputs() -> None:
    assert reg.openrouter_auto_uses_instructor_structured_outputs(
        base_url="https://openrouter.ai/api/v1",
        model_id="anthropic/claude-sonnet-4.6",
    )


def test_user_requested_pricing_rows() -> None:
    km = reg.get_openrouter_model_profile("moonshotai/kimi-k2.6")
    assert km is not None
    assert km.prompt_usd_per_1m_tokens == 0.74
    assert km.completion_usd_per_1m_tokens == 3.49

    qw = reg.get_openrouter_model_profile("qwen/qwen3-235b-a22b-2507")
    assert qw is not None
    assert qw.prompt_usd_per_1m_tokens == 0.071
    assert qw.completion_usd_per_1m_tokens == 0.1

    ds = reg.get_openrouter_model_profile("deepseek/deepseek-v4-pro")
    assert ds is not None
    assert ds.prompt_usd_per_1m_tokens == 0.485
    assert ds.completion_usd_per_1m_tokens == 0.87

    mx = reg.get_openrouter_model_profile("minimax/minimax-m2.7")
    assert mx is not None
    assert mx.prompt_usd_per_1m_tokens == 0.3
    assert mx.completion_usd_per_1m_tokens == 1.2


def test_qwen_397_reasoning_extra_body() -> None:
    assert reg.openrouter_auto_reasoning_extra_body(
        base_url="https://openrouter.ai/api/v1",
        model_id="qwen/qwen3.5-397b-a17b",
    )
    assert not reg.openrouter_auto_reasoning_extra_body(
        base_url="https://openrouter.ai/api/v1",
        model_id="openai/gpt-4o",
    )


def test_pricing_run_metadata_builds_optional_slices() -> None:
    blob = reg.openrouter_reference_pricing_run_metadata(
        base_url="https://openrouter.ai/api/v1",
        chat_model_id="openai/gpt-4o-mini",
        extraction_model_id="qwen/qwen3.5-397b-a17b",
    )
    assert "openrouter_reference_pricing_usd_per_1m" in blob
    inner = blob["openrouter_reference_pricing_usd_per_1m"]
    assert inner["chat"]["prompt_usd_per_1m"] == 0.15
    assert inner["extraction"]["model_id"] == "qwen/qwen3.5-397b-a17b"
