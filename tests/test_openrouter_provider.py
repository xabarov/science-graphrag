from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from science_graphrag.embeddings.errors import (
    EmbeddingEmptyPayloadError,
    EmbeddingProviderUnavailableError,
)
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
        embeddings=SimpleNamespace(
            create=lambda **_kwargs: SimpleNamespace(data=None, model="bad-model")
        )
    )

    with pytest.raises(EmbeddingEmptyPayloadError, match="returned no data"):
        provider.embed(["hello"])


def test_call_openrouter_raises_clear_error_when_embedding_missing(tmp_path: Path) -> None:
    provider = _provider(tmp_path)
    provider.__dict__["_client"] = SimpleNamespace(
        embeddings=SimpleNamespace(
            create=lambda **_kwargs: SimpleNamespace(
                data=[SimpleNamespace(embedding=None)], model="bad-model"
            )
        )
    )

    with pytest.raises(EmbeddingEmptyPayloadError, match="missing embedding"):
        provider.embed(["hello"])


def test_call_openrouter_provider_unavailable_on_404_payload(tmp_path: Path) -> None:
    class _Resp:  # pylint: disable=too-few-public-methods
        data = None
        model = "baai/bge-m3"

        def model_dump(self):
            return {"error": {"message": "No successful provider responses.", "code": 404}}

    provider = _provider(tmp_path)
    provider.__dict__["_client"] = SimpleNamespace(
        embeddings=SimpleNamespace(create=lambda **_kwargs: _Resp()),
    )
    with pytest.raises(EmbeddingProviderUnavailableError, match="no successful provider"):
        provider.embed(["x"])
