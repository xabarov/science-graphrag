"""Shared HTTP helpers for external research tools (User-Agent, polite-pool contact)."""

from __future__ import annotations

from science_graphrag.config import Settings
from science_graphrag.ingestion.enrichment.openalex import OPENALEX_MAILTO_FALLBACK


def external_research_user_agent(settings: Settings) -> str:
    """User-Agent string aligned with ingestion OpenAlex polite-pool policy."""
    mailto = (settings.openalex_mailto or OPENALEX_MAILTO_FALLBACK).strip()
    return f"science-graphrag/0.1 (mailto:{mailto})"


__all__ = ["external_research_user_agent"]
