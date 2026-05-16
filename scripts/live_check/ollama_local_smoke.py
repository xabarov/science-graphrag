#!/usr/bin/env python3
"""Live smoke for local Ollama + SciGraph settings integration.

Checks:
- API contour health (`GET /health`)
- Raw Ollama OpenAI-compatible endpoints (`/v1/chat/completions`, `/v1/embeddings`)
- Settings PATCH to Ollama-compatible `llm.tasks`
- Settings diagnostics (`probable_ollama_endpoint`)
- Settings probe (`POST /v1/settings/llm/test`)

Environment (optional):
    AGENT_LIVE_BASE
    AGENT_LIVE_AUTHORIZATION
    AGENT_LIVE_ADMIN_KEY
    OLLAMA_BASE_URL
    OLLAMA_CHAT_MODEL
    OLLAMA_EMBED_MODEL
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import httpx

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent
_DEFAULT_OLLAMA_BASE = "http://127.0.0.1:11434/v1"
_DEFAULT_CHAT_MODEL = "gemma4"
_DEFAULT_EMBED_MODEL = "qwen3-embedding:0.6b"


def _extra_headers() -> dict[str, str]:
    out: dict[str, str] = {}
    auth = (os.environ.get("AGENT_LIVE_AUTHORIZATION") or "").strip()
    if auth:
        out["Authorization"] = auth
    admin = (os.environ.get("AGENT_LIVE_ADMIN_KEY") or "").strip()
    if admin:
        out["X-Admin-Key"] = admin
    return out


def _ensure_ok_json(resp: httpx.Response, *, op: str) -> dict[str, Any]:
    if resp.status_code >= 400:
        raise RuntimeError(f"{op}: HTTP {resp.status_code}: {resp.text[:400]}")
    try:
        payload = resp.json()
    except ValueError as exc:  # pragma: no cover - runtime-only branch
        raise RuntimeError(f"{op}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{op}: invalid JSON shape (expected object)")
    return payload


def _check_raw_ollama(base_url: str, chat_model: str, embeddings_model: str, timeout: float) -> None:
    headers = {"Content-Type": "application/json", "Authorization": "Bearer ollama"}
    with httpx.Client(timeout=timeout) as client:
        chat_resp = client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": chat_model,
                "messages": [{"role": "user", "content": "Reply with exactly OK"}],
                "stream": False,
                "max_tokens": 16,
            },
        )
        chat_payload = _ensure_ok_json(chat_resp, op="ollama_chat")
        choices = chat_payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("ollama_chat: missing choices[]")
        print("ollama_chat_ok=1")

        emb_resp = client.post(
            f"{base_url}/embeddings",
            headers=headers,
            json={"model": embeddings_model, "input": ["hello", "world"]},
        )
        emb_payload = _ensure_ok_json(emb_resp, op="ollama_embeddings")
        emb_data = emb_payload.get("data")
        if not isinstance(emb_data, list) or len(emb_data) < 1:
            raise RuntimeError("ollama_embeddings: missing data[]")
        first = emb_data[0] if emb_data else {}
        vector = first.get("embedding") if isinstance(first, dict) else None
        if not isinstance(vector, list) or not vector:
            raise RuntimeError("ollama_embeddings: missing embedding vector")
        print(f"ollama_embeddings_ok=1 dim={len(vector)}")


def _patch_settings_to_ollama(
    llm_base_url: str,
    *,
    api_base: str,
    chat_model: str,
    embeddings_model: str,
    timeout: float,
) -> None:
    payload = {
        "tasks": {
            "extraction": {
                "base_url": llm_base_url,
                "model": chat_model,
                "temperature": 0.0,
                "timeout_seconds": 300,
            },
            "chat": {
                "base_url": llm_base_url,
                "model": chat_model,
                "temperature": 0.0,
                "timeout_seconds": 300,
            },
            "vision": {
                "base_url": llm_base_url,
                "model": "llava",
                "temperature": 0.0,
                "timeout_seconds": 300,
            },
            "embeddings": {
                "mode": "http",
                "base_url": llm_base_url,
                "model": embeddings_model,
                "timeout_seconds": 120,
            },
        },
        "api_key": "ollama",
        "chat_api_key": "ollama",
        "vision_api_key": "ollama",
        "embeddings_api_key": "ollama",
    }
    headers = _extra_headers()
    with httpx.Client(timeout=timeout, headers=headers) as client:
        patch_resp = client.patch(f"{api_base}/v1/settings/llm", json=payload)
        patch_body = _ensure_ok_json(patch_resp, op="patch_llm_settings")
        llm = patch_body.get("llm") if isinstance(patch_body, dict) else None
        if not isinstance(llm, dict):
            raise RuntimeError("patch_llm_settings: response missing llm block")
        print("settings_patch_ok=1")

        get_resp = client.get(f"{api_base}/v1/settings")
        get_body = _ensure_ok_json(get_resp, op="get_settings")
        llm_snapshot = get_body.get("llm") if isinstance(get_body, dict) else None
        if not isinstance(llm_snapshot, dict):
            raise RuntimeError("get_settings: missing llm snapshot")
        diagnostics = llm_snapshot.get("diagnostics")
        if not isinstance(diagnostics, dict):
            raise RuntimeError("get_settings: missing llm.diagnostics")
        probable = bool(diagnostics.get("probable_ollama_endpoint"))
        expects_probable = "11434" in llm_base_url and llm_base_url.rstrip("/").endswith("/v1")
        if expects_probable and probable is not True:
            raise RuntimeError("get_settings: expected llm.diagnostics.probable_ollama_endpoint=true")
        print(
            "settings_diagnostics_ok=1 "
            f"probable_ollama_endpoint={str(probable).lower()} "
            f"expects_probable={str(expects_probable).lower()}"
        )

        test_resp = client.post(
            f"{api_base}/v1/settings/llm/test",
            json={
                "base_url": llm_base_url,
                "model": chat_model,
                "api_key": "ollama",
                "temperature": 0.0,
                "timeout_seconds": 120,
                "use_saved_secret": False,
            },
        )
        test_body = _ensure_ok_json(test_resp, op="llm_test_saved")
        status = str(test_body.get("status") or "").strip().lower()
        if status not in {"connected", "ok"}:
            raise RuntimeError(f"llm_test_saved: unexpected status={status!r} body={test_body}")
        print(f"settings_llm_test_ok=1 status={status}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Local Ollama + SciGraph live smoke.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("AGENT_LIVE_BASE", "http://127.0.0.1:18787"),
        help="SciGraph API base URL (default: AGENT_LIVE_BASE or http://127.0.0.1:18787)",
    )
    parser.add_argument(
        "--ollama-base-url",
        default=os.environ.get("OLLAMA_BASE_URL", _DEFAULT_OLLAMA_BASE),
        help="Ollama OpenAI-compatible base URL (default: http://127.0.0.1:11434/v1)",
    )
    parser.add_argument(
        "--settings-ollama-base-url",
        default=os.environ.get("OLLAMA_SETTINGS_BASE_URL", "").strip(),
        help=(
            "Optional Ollama base URL persisted into /v1/settings/llm tasks. "
            "Use when API runs in Docker and cannot reach host localhost."
        ),
    )
    parser.add_argument(
        "--chat-model",
        default=os.environ.get("OLLAMA_CHAT_MODEL", _DEFAULT_CHAT_MODEL),
        help=f"Ollama chat model (default: {_DEFAULT_CHAT_MODEL})",
    )
    parser.add_argument(
        "--embeddings-model",
        default=os.environ.get("OLLAMA_EMBED_MODEL", _DEFAULT_EMBED_MODEL),
        help=f"Ollama embeddings model (default: {_DEFAULT_EMBED_MODEL})",
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout seconds")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=_REPO_ROOT / ".env",
        help="Dotenv path loaded before checks (default: repo .env)",
    )
    args = parser.parse_args()

    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))

    from dotenv_util import (  # pylint: disable=import-outside-toplevel,import-error
        load_dotenv_or_warn,
        resolve_live_base_url,
    )

    load_dotenv_or_warn(args.env_file)
    api_base = resolve_live_base_url(args.base_url)
    ollama_base = str(args.ollama_base_url or "").strip().rstrip("/")
    settings_ollama_base = str(args.settings_ollama_base_url or "").strip().rstrip("/") or ollama_base
    if not ollama_base:
        raise RuntimeError("missing --ollama-base-url")

    headers = _extra_headers()
    with httpx.Client(timeout=args.timeout, headers=headers) as client:
        health_resp = client.get(f"{api_base}/health")
        _ensure_ok_json(health_resp, op="health")
    print("api_health_ok=1")

    _check_raw_ollama(
        ollama_base,
        chat_model=args.chat_model.strip(),
        embeddings_model=args.embeddings_model.strip(),
        timeout=args.timeout,
    )
    _patch_settings_to_ollama(
        settings_ollama_base,
        api_base=api_base,
        chat_model=args.chat_model.strip(),
        embeddings_model=args.embeddings_model.strip(),
        timeout=args.timeout,
    )
    print("ollama_live_smoke_ok=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
