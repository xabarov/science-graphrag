"""Tracer registration for Phoenix (OTLP) + optional auto-instrumentation.

**Manual vs automatic LLM spans (agent chat):**

- ``setup_langchain_instrumentation()`` enables OpenInference LangChain hooks (LangGraph included).
- Domain contract spans (``agent.query``, ``tool.*``, ``retrieval.*``, explicit ``llm.agent.*``)
  are **hand-authored** in the agent runtime for stable naming and attributes.
- OpenAI auto-instrumentation is optional (``PHOENIX_OPENAI_AUTO_INSTRUMENTATION``); disable if it
  duplicates ``llm_span`` noise. See ``docs/architecture/observability-phoenix.md``.
"""

from __future__ import annotations

import importlib
import os
import socket
from functools import lru_cache

from phoenix.otel import register

from science_graphrag.observability.instrumentation import setup_langchain_instrumentation
from science_graphrag.observability.scope import is_extraction_llm_scope


@lru_cache(maxsize=1)
def init_tracer_provider() -> None:
    """Initialize Phoenix tracer provider once per process."""
    endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
    project_name = os.getenv("PHOENIX_PROJECT_NAME", "science-graphrag")
    api_key = os.getenv("PHOENIX_API_KEY") or None

    if endpoint:
        if "phoenix" in endpoint:
            try:
                socket.getaddrinfo("phoenix", 6006)
            except OSError:
                endpoint = endpoint.replace("phoenix", "localhost")

        normalized = endpoint.rstrip("/")
        if normalized.endswith(":6006"):
            endpoint = f"{normalized}/v1/traces"

    batch = os.getenv("ENV", "dev").lower() not in {"dev", "local", "test"}

    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    register(
        project_name=project_name,
        endpoint=endpoint,
        batch=batch,
        headers=headers or None,
    )
    setup_langchain_instrumentation()
    _register_optional_openai_instrumentation()


@lru_cache(maxsize=1)
def _register_optional_openai_instrumentation() -> None:
    if is_extraction_llm_scope():
        return
    if os.getenv("PHOENIX_OPENAI_AUTO_INSTRUMENTATION", "1").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }:
        return
    try:
        module = importlib.import_module("openinference.instrumentation.openai")
        instrumentor_cls = getattr(module, "OpenAIInstrumentor", None)
        if instrumentor_cls is None:
            return
        instrumentor_cls().instrument()
    except Exception:
        return
