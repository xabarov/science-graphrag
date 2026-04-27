"""Typed failures for embedding providers (OpenRouter / OpenAI-compatible)."""

from __future__ import annotations


class EmbeddingCallError(RuntimeError):
    """Base class for embedding failures with operator-facing ``code``."""

    code: str
    retryable: bool

    def __init__(self, message: str, *, code: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class EmbeddingProviderUnavailableError(EmbeddingCallError):
    """Upstream had no healthy provider (e.g. OpenRouter ``No successful provider responses``)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="provider_unavailable", retryable=True)


class EmbeddingEmptyPayloadError(EmbeddingCallError):
    """HTTP 200 but missing ``data`` or per-item ``embedding`` vectors."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="empty_payload", retryable=True)


class EmbeddingNonRetryableHttpError(EmbeddingCallError):
    """4xx other than rate-limit; do not spin retries indefinitely."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        suffix = f" (http={status_code})" if status_code is not None else ""
        super().__init__(message + suffix, code="non_retryable_4xx", retryable=False)
        self.status_code = status_code


class EmbeddingPartialPayloadError(EmbeddingCallError):
    """Fewer vectors returned than inputs (after non-null data list)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="partial_payload", retryable=True)
