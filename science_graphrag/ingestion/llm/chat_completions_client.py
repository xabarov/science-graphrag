"""Shared chat-completions HTTP entrypoints for non-Instructor ingest callers (VL, etc.)."""

from __future__ import annotations

from typing import Any

from science_graphrag.ingestion.llm.raw_openai_transport import post_chat_completions_json
from science_graphrag.utils.project_logging import get_logger


def ingest_chat_completions_json(
    *,
    transport_role: str,
    base_url: str,
    api_key: str,
    json_body: dict[str, Any],
    timeout_seconds: float = 300.0,
    max_transport_retries: int = 3,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """POST ``/chat/completions`` with ingest-standard logging and retry policy.

    ``transport_role`` becomes the logger suffix (e.g. ``vl_pdf``) so VL and
    future raw transports share one implementation without pulling Instructor.
    """
    logger = get_logger(f"ingestion.llm.transport.{transport_role}")
    logger.debug(
        "chat_completions POST role=%s model=%s timeout_s=%s",
        transport_role,
        json_body.get("model"),
        timeout_seconds,
    )
    return post_chat_completions_json(
        base_url=base_url,
        api_key=api_key,
        json_body=json_body,
        timeout_seconds=timeout_seconds,
        max_transport_retries=max_transport_retries,
    )
