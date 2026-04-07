"""Shared resolution of OpenRouter/OpenAI-compatible settings for benchmark teacher runs."""

from __future__ import annotations

import argparse

from science_graphrag.config import Settings


def teacher_extraction_settings(base: Settings, args: argparse.Namespace) -> Settings:
    """Prefer CLI, then ``benchmark_teacher_*``, then extraction LLM fields."""

    api = (
        (getattr(args, "api_key", None) or "").strip()
        or (base.benchmark_teacher_llm_api_key or "").strip()
        or (base.extraction_llm_api_key or "").strip()
    )
    url = (
        (getattr(args, "base_url", None) or "").strip()
        or (base.benchmark_teacher_llm_base_url or "").strip()
        or base.extraction_llm_base_url
    )
    model = (
        (getattr(args, "model", None) or "").strip()
        or (base.benchmark_teacher_llm_model or "").strip()
        or "deepseek/deepseek-v3.2"
    )
    return base.model_copy(
        update={
            "extraction_llm_enabled": True,
            "extraction_llm_api_key": api or None,
            "extraction_llm_base_url": url,
            "extraction_llm_model": model,
        },
    )
