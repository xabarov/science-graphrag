"""Heuristic fallback modules for ingestion LLM extraction."""

from science_graphrag.ingestion.llm.heuristics import (
    authorships,
    chunking,
    metadata,
    references,
    semantic,
)

__all__ = ["metadata", "authorships", "references", "semantic", "chunking"]
