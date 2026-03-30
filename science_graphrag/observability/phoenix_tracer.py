"""
Minimal Phoenix / OpenTelemetry init for science-graphrag (aligned with osint-gr patterns).
"""

from __future__ import annotations

import importlib
import json
import os
import socket
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterator

from opentelemetry import trace as trace_api
from opentelemetry.trace import SpanKind, Status, StatusCode, Tracer
from phoenix.otel import register

# ``full`` — все ручные chain_span / llm_span и (опционально) OpenAI auto-instrumentation.
# ``extraction_llm`` — только извлечение layer-1 (три LLM-вызова) плюс родительские CHAIN
# из списка ниже; без VL PDF, без Neo4j/Qdrant/OpenAlex и без fallback.chain из stage_extraction.
_PHOENIX_TRACE_SCOPE_FULL = "full"
_PHOENIX_TRACE_SCOPE_EXTRACTION_LLM = "extraction_llm"

_EXTRACTION_LLM_CHAIN_NAMES = frozenset({"ingest_document", "metadata_and_references_extraction"})
_EXTRACTION_LLM_MANUAL_LLM_NAMES = frozenset(
    {
        "llm.metadata_extraction",
        "llm.authorships_extraction",
        "llm.references_extraction",
    }
)


class SpanKindOI:
    """OpenInference span kinds for Phoenix UI."""

    LLM = "LLM"
    CHAIN = "CHAIN"
    RETRIEVER = "RETRIEVER"
    TOOL = "TOOL"


class OpenInferenceAttributes:
    """OpenInference semantic convention attribute keys used by this project."""

    SPAN_KIND = "openinference.span.kind"
    INPUT_VALUE = "input.value"
    INPUT_MIME_TYPE = "input.mime_type"
    OUTPUT_VALUE = "output.value"
    OUTPUT_MIME_TYPE = "output.mime_type"
    SESSION_ID = "session.id"
    USER_ID = "user.id"


MIME_TYPE_TEXT = "text/plain"
MIME_TYPE_JSON = "application/json"
DEFAULT_SPAN_PAYLOAD_LIMIT = 4000


def phoenix_trace_scope() -> str:
    """OTel/Phoenix verbosity: ``full`` (default) or ``extraction_llm``."""

    return os.getenv("PHOENIX_TRACE_SCOPE", _PHOENIX_TRACE_SCOPE_FULL).strip().lower()


def _is_extraction_llm_scope() -> bool:
    return phoenix_trace_scope() == _PHOENIX_TRACE_SCOPE_EXTRACTION_LLM


@contextmanager
def _noop_span_context() -> Iterator[None]:
    yield None


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
    _register_optional_openai_instrumentation()


@lru_cache(maxsize=1)
def _register_optional_openai_instrumentation() -> None:
    if _is_extraction_llm_scope():
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


def add_span_event(name: str, attributes: dict[str, Any] | None = None) -> None:
    """Emit a timed event on the current span (Phoenix / OTLP)."""
    span = trace_api.get_current_span()
    if span.is_recording():
        span.add_event(name, attributes=attributes or {})


def set_span_attribute(key: str, value: Any) -> None:
    """Set an attribute on the current span when recording is active."""
    span = trace_api.get_current_span()
    if span.is_recording() and value is not None and value != "":
        span.set_attribute(key, value)


def set_span_attributes(attributes: dict[str, Any]) -> None:
    """Set multiple attributes on the current span."""
    for key, value in attributes.items():
        set_span_attribute(key, value)


def set_span_error(exception: BaseException) -> None:
    """Mark the current span as failed without re-raising."""
    span = trace_api.get_current_span()
    if span.is_recording():
        span.set_status(Status(StatusCode.ERROR, str(exception)))
        span.record_exception(exception)


@lru_cache(maxsize=8)
def get_tracer(name: str = "science-graphrag") -> Tracer:
    """OpenTelemetry tracer bound to Phoenix exporter."""
    init_tracer_provider()
    return trace_api.get_tracer(name)


@contextmanager
def chain_span(name: str, attributes: dict[str, Any] | None = None):
    """CHAIN-style span for phase grouping in Phoenix."""
    if _is_extraction_llm_scope() and name not in _EXTRACTION_LLM_CHAIN_NAMES:
        with _noop_span_context():
            yield None
        return
    with get_tracer().start_as_current_span(name, kind=SpanKind.CLIENT) as span:
        span.set_attribute(OpenInferenceAttributes.SPAN_KIND, SpanKindOI.CHAIN)
        if attributes:
            set_span_attributes(attributes)
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise


@contextmanager
def llm_span(name: str, attributes: dict[str, Any] | None = None):
    """LLM-style span (manual chat / extraction calls)."""
    if _is_extraction_llm_scope() and name not in _EXTRACTION_LLM_MANUAL_LLM_NAMES:
        with _noop_span_context():
            yield None
        return
    with get_tracer().start_as_current_span(name, kind=SpanKind.CLIENT) as span:
        span.set_attribute(OpenInferenceAttributes.SPAN_KIND, SpanKindOI.LLM)
        if attributes:
            set_span_attributes(attributes)
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise


class SpanAttributes:
    """Helpers for OpenInference-compatible Phoenix attributes."""

    @staticmethod
    def _system_from_model(model: str | None) -> str | None:
        if not model:
            return None
        provider_hint = model.lower().split("/", maxsplit=1)[0]
        known = {
            "anthropic": "anthropic",
            "cohere": "cohere",
            "deepseek": "deepseek",
            "google": "google",
            "groq": "groq",
            "meta": "meta",
            "mistralai": "mistralai",
            "openai": "openai",
            "xai": "xai",
        }
        return known.get(provider_hint)

    @staticmethod
    def _provider_from_model(model: str | None) -> str | None:
        if not model:
            return None
        model_l = model.lower()
        if "/" in model_l:
            prefix = model_l.split("/", maxsplit=1)[0]
            return {
                "anthropic": "anthropic",
                "cohere": "cohere",
                "deepseek": "deepseek",
                "google": "google",
                "groq": "groq",
                "meta": "meta",
                "mistralai": "mistralai",
                "openai": "openai",
                "xai": "xai",
            }.get(prefix, prefix)
        if model_l.startswith(("gpt", "o1", "o3", "o4")):
            return "openai"
        if model_l.startswith("claude"):
            return "anthropic"
        if model_l.startswith("gemini"):
            return "google"
        if model_l.startswith("mistral"):
            return "mistralai"
        return None

    @staticmethod
    def _provider_from_base_url(base_url: str | None) -> str | None:
        if not base_url:
            return None
        url = base_url.lower()
        if "openrouter.ai" in url:
            return "openrouter"
        if "api.openai.com" in url:
            return "openai"
        if "anthropic.com" in url:
            return "anthropic"
        if "googleapis.com" in url or "generativelanguage.googleapis.com" in url:
            return "google"
        if "localhost" in url or "127.0.0.1" in url:
            return "local"
        return None

    @staticmethod
    def _safe_json(value: Any, *, limit: int | None = None) -> str:
        if isinstance(value, str):
            serialized = value
        else:
            try:
                serialized = json.dumps(value, ensure_ascii=False, default=str)
            except TypeError:
                serialized = str(value)
        max_len = (
            limit
            if limit is not None
            else int(os.getenv("PHOENIX_SPAN_IO_MAX_LEN", str(DEFAULT_SPAN_PAYLOAD_LIMIT)))
        )
        if max_len > 0 and len(serialized) > max_len:
            return serialized[:max_len] + "...[truncated]"
        return serialized

    @staticmethod
    def set_input(value: str | dict[str, Any] | list[Any], mime_type: str = MIME_TYPE_TEXT) -> None:
        """Set generic input payload on the current span."""
        if isinstance(value, (dict, list)):
            value = SpanAttributes._safe_json(value)
            mime_type = MIME_TYPE_JSON
        set_span_attribute(OpenInferenceAttributes.INPUT_VALUE, value)
        set_span_attribute(OpenInferenceAttributes.INPUT_MIME_TYPE, mime_type)

    @staticmethod
    def set_output(
        value: str | dict[str, Any] | list[Any], mime_type: str = MIME_TYPE_TEXT
    ) -> None:
        """Set generic output payload on the current span."""
        if isinstance(value, (dict, list)):
            value = SpanAttributes._safe_json(value)
            mime_type = MIME_TYPE_JSON
        set_span_attribute(OpenInferenceAttributes.OUTPUT_VALUE, value)
        set_span_attribute(OpenInferenceAttributes.OUTPUT_MIME_TYPE, mime_type)

    @staticmethod
    def set_llm_attrs(
        model: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        base_url: str | None = None,
    ) -> None:
        """Set standard LLM metadata for Phoenix/OpenInference."""
        set_span_attribute("llm.model_name", model)
        system = SpanAttributes._system_from_model(model)
        if system:
            set_span_attribute("llm.system", system)
        provider = SpanAttributes._provider_from_base_url(
            base_url
        ) or SpanAttributes._provider_from_model(model)
        if provider:
            set_span_attribute("llm.provider", provider)
        if temperature is not None:
            set_span_attribute("llm.temperature", temperature)
        if max_tokens is not None:
            set_span_attribute("llm.max_tokens", max_tokens)
        SpanAttributes.set_llm_token_counts(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            usage_source="api",
        )

    @staticmethod
    def set_llm_invocation_parameters(parameters: dict[str, Any]) -> None:
        """Set invocation params as JSON payload."""
        set_span_attribute("llm.invocation_parameters", SpanAttributes._safe_json(parameters))

    @staticmethod
    def _set_message_attributes(prefix: str, message: dict[str, Any]) -> None:
        role = message.get("role")
        content = message.get("content")
        name = message.get("name")
        if role:
            set_span_attribute(f"{prefix}.message.role", str(role))
        if name:
            set_span_attribute(f"{prefix}.message.name", str(name))
        if content is not None:
            set_span_attribute(f"{prefix}.message.content", SpanAttributes._safe_json(content))

        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list):
            for idx, tool_call in enumerate(tool_calls):
                if not isinstance(tool_call, dict):
                    continue
                call_prefix = f"{prefix}.message.tool_calls.{idx}"
                tool_call_id = tool_call.get("id")
                function_payload = tool_call.get("function") or {}
                if tool_call_id:
                    set_span_attribute(f"{call_prefix}.tool_call.id", str(tool_call_id))
                if isinstance(function_payload, dict):
                    function_name = function_payload.get("name")
                    function_args = function_payload.get("arguments")
                    if function_name:
                        set_span_attribute(
                            f"{call_prefix}.tool_call.function.name", str(function_name)
                        )
                    if function_args is not None:
                        set_span_attribute(
                            f"{call_prefix}.tool_call.function.arguments",
                            SpanAttributes._safe_json(function_args),
                        )

    @staticmethod
    def set_llm_input_messages(messages: list[dict[str, Any]]) -> None:
        """Flatten chat request messages into OpenInference attributes."""
        for idx, message in enumerate(messages):
            SpanAttributes._set_message_attributes(f"llm.input_messages.{idx}", message)

    @staticmethod
    def set_llm_output_messages(messages: list[dict[str, Any]]) -> None:
        """Flatten chat response messages into OpenInference attributes."""
        for idx, message in enumerate(messages):
            SpanAttributes._set_message_attributes(f"llm.output_messages.{idx}", message)

    @staticmethod
    def estimate_token_count(text: str | None) -> int:
        """Conservative token estimate for cost fallback when API usage is unavailable."""
        if not text:
            return 0
        normalized = " ".join(text.split())
        if not normalized:
            return 0
        return max(1, (len(normalized) + 3) // 4)

    @staticmethod
    def set_llm_token_counts(
        *,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        usage_source: str = "api",
    ) -> None:
        """Set Phoenix-compatible token count fields."""
        if prompt_tokens is not None:
            set_span_attribute("llm.token_count.prompt", int(prompt_tokens))
        if completion_tokens is not None:
            set_span_attribute("llm.token_count.completion", int(completion_tokens))
        computed_total = total_tokens
        if computed_total is None and prompt_tokens is not None and completion_tokens is not None:
            computed_total = int(prompt_tokens) + int(completion_tokens)
        if computed_total is not None:
            set_span_attribute("llm.token_count.total", int(computed_total))
        set_span_attribute("llm.usage_source", usage_source)

    @staticmethod
    def set_llm_token_counts_from_text(
        *,
        prompt_text: str,
        completion_text: str,
        usage_source: str = "estimated",
    ) -> None:
        """Estimate token counts from prompt/completion text."""
        SpanAttributes.set_llm_token_counts(
            prompt_tokens=SpanAttributes.estimate_token_count(prompt_text),
            completion_tokens=SpanAttributes.estimate_token_count(completion_text),
            usage_source=usage_source,
        )

    @staticmethod
    def set_tool_attrs(
        tool_name: str, tool_type: str = "tool", tool_description: str | None = None
    ) -> None:
        """Attach TOOL span metadata for future agent/tool tracing."""
        set_span_attribute("tool.name", tool_name)
        set_span_attribute("tool.type", tool_type)
        if tool_description:
            set_span_attribute("tool.description", tool_description)

    @staticmethod
    def set_tool_parameters(parameters: dict[str, Any] | list[Any] | str) -> None:
        """Attach TOOL input parameters."""
        set_span_attribute("tool.parameters", SpanAttributes._safe_json(parameters))


@contextmanager
def traced_tool_span(
    name: str,
    *,
    tool_name: str,
    tool_type: str = "tool",
    tool_parameters: dict[str, Any] | list[Any] | str | None = None,
    tool_description: str | None = None,
):
    """Create a TOOL span compatible with Phoenix/OpenInference."""
    with get_tracer().start_as_current_span(name) as span:
        span.set_attribute(OpenInferenceAttributes.SPAN_KIND, SpanKindOI.TOOL)
        SpanAttributes.set_tool_attrs(
            tool_name, tool_type=tool_type, tool_description=tool_description
        )
        if tool_parameters is not None:
            SpanAttributes.set_tool_parameters(tool_parameters)
            SpanAttributes.set_input(tool_parameters, mime_type=MIME_TYPE_JSON)
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise
