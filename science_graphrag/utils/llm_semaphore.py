"""Async semaphore factory for LLM concurrency caps (LX1 foundation)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from science_graphrag.config import Settings


def build_llm_semaphore_map(settings: "Settings") -> dict[str, asyncio.Semaphore]:
    """Named pools for future translation / extraction / claims paths."""

    return {
        "default": asyncio.Semaphore(max(1, int(settings.llm_concurrency_default))),
        "translation": asyncio.Semaphore(max(1, int(settings.llm_concurrency_translation))),
        "extraction_references": asyncio.Semaphore(
            max(1, int(settings.llm_concurrency_extraction_references)),
        ),
        "claims": asyncio.Semaphore(max(1, int(settings.llm_concurrency_claims))),
        "summary": asyncio.Semaphore(max(1, int(settings.llm_concurrency_summary))),
    }
