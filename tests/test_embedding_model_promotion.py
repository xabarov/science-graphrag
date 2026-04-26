"""ADR-021: SCIENCE_GRAPHRAG_EMBEDDING_MODEL with slash promotes to OpenRouter slot."""

from __future__ import annotations

from science_graphrag.config import Settings


def test_embedding_model_hub_id_promotes_to_openrouter() -> None:
    s = Settings.model_validate({"embedding_model": "baai/bge-m3"})
    assert s.openrouter_embedding_model == "baai/bge-m3"
    assert s.embedding_model is None
