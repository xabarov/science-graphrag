"""Shared HTTP transport for OpenAI-compatible ``/chat/completions`` (non-Instructor paths)."""

from __future__ import annotations

import time
from typing import Any

import httpx


def post_chat_completions_json(
    *,
    base_url: str,
    api_key: str,
    json_body: dict[str, Any],
    timeout_seconds: float = 300.0,
    max_transport_retries: int = 3,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    POST ``{base_url}/chat/completions`` with bounded transport retries.

    Returns ``(response_json, usage_dict)`` where ``usage_dict`` may be empty.
    """

    attempts = max(1, int(max_transport_retries))
    root = base_url.rstrip("/")
    url = f"{root}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    total_wait = 0.0
    for attempt in range(attempts):
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(url, headers=headers, json=json_body)
                response.raise_for_status()
                data = response.json()
            usage = data.get("usage") or {}
            if not isinstance(usage, dict):
                usage = {}
            return data, usage
        except (httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.ConnectError) as exc:
            wait_s = float(2 ** (attempt + 1))
            total_wait += wait_s
            if attempt >= attempts - 1 or total_wait > 60.0:
                raise exc
            time.sleep(wait_s)
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code if exc.response is not None else None
            if code is not None and 500 <= code < 600 and attempt < attempts - 1:
                wait_s = float(2 ** (attempt + 1))
                total_wait += wait_s
                time.sleep(wait_s)
                continue
            raise
    raise AssertionError("post_chat_completions_json: unreachable")  # pragma: no cover
