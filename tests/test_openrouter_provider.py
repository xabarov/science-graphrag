from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from science_graphrag.embeddings.openrouter_provider import (
    OpenRouterEmbeddingProvider,
    OpenRouterEmbeddingSettings,
)


def _provider(tmp_path: Path) -> OpenRouterEmbeddingProvider:
    return OpenRouterEmbeddingProvider(
        OpenRouterEmbeddingSettings(
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1",
            model="baai/bge-m3",
            cache_root=tmp_path,
            batch_size=8,
        )
    )


def test_call_openrouter_raises_clear_error_when_data_missing(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    provider.__dict__["_client"] = SimpleNamespace(
        embeddings=SimpleNamespace(create=lambda **_kwargs: SimpleNamespace(data=None, model="bad-model"))
    )

    with pytest.raises(RuntimeError, match="returned no data"):
        provider.embed(["hello"])


def test_call_openrouter_raises_clear_error_when_embedding_missing(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    provider.__dict__["_client"] = SimpleNamespace(
        embeddings=SimpleNamespace(
            create=lambda **_kwargs: SimpleNamespace(data=[SimpleNamespace(embedding=None)], model="bad-model")
        )
    ) 

    with pytest.raises(RuntimeError, match="missing embedding"):
        provider.embed(["hello"])
