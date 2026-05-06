"""Unit tests for ``classify_agent_stream_error``.

The classifier maps common LangChain / OpenRouter failures to a small,
stable enum of ``error_class`` values used by the SSE ``error`` event so the
UI can localize them via ``chat.errors.<error_class>`` keys.
"""

from __future__ import annotations

from science_graphrag.api.agent_v2_modules.errors import classify_agent_stream_error


def test_classify_provider_unauthorized_from_value_error_dict() -> None:
    exc = ValueError({"code": 401, "message": "invalid api key"})
    cls, msg = classify_agent_stream_error(exc)
    assert cls == "provider_unauthorized"
    assert "401" in msg


def test_classify_provider_forbidden_from_value_error_dict() -> None:
    exc = ValueError({"code": 403, "message": "quota exceeded"})
    cls, msg = classify_agent_stream_error(exc)
    assert cls == "provider_forbidden"
    assert "403" in msg


def test_classify_provider_rejected_for_other_status_codes() -> None:
    exc = ValueError({"code": 502, "message": "bad gateway"})
    cls, msg = classify_agent_stream_error(exc)
    assert cls == "provider_rejected"
    assert "502" in msg


def test_classify_provider_rejected_when_no_status_code() -> None:
    exc = ValueError({"message": "no model selected"})
    cls, msg = classify_agent_stream_error(exc)
    assert cls == "provider_rejected"
    assert "no model selected" in msg


def test_classify_provider_timeout_from_exception_name() -> None:
    class _MyTimeoutError(Exception):
        pass

    cls, _msg = classify_agent_stream_error(_MyTimeoutError("read timed out"))
    assert cls == "provider_timeout"


def test_classify_provider_unreachable_from_connection_error_name() -> None:
    cls, _msg = classify_agent_stream_error(ConnectionError("DNS lookup failed"))
    assert cls == "provider_unreachable"


def test_classify_provider_timeout_from_error_message() -> None:
    cls, _msg = classify_agent_stream_error(RuntimeError("request timed out after 30s"))
    assert cls == "provider_timeout"


def test_classify_provider_unreachable_from_error_message() -> None:
    cls, _msg = classify_agent_stream_error(RuntimeError("connection refused by upstream"))
    assert cls == "provider_unreachable"


def test_classify_internal_error_for_unknown_exception() -> None:
    cls, msg = classify_agent_stream_error(RuntimeError("kaboom"))
    assert cls == "internal_error"
    assert "kaboom" in msg


def test_classify_agent_turn_deadline() -> None:
    from science_graphrag.agent.graph.errors import AgentGraphDeadlineExceeded

    cls, msg = classify_agent_stream_error(AgentGraphDeadlineExceeded(timeout_seconds=42.0))
    assert cls == "agent_turn_deadline_exceeded"
    assert "time limit" in msg.lower()


def test_classify_pydantic_validation_error() -> None:
    from pydantic import BaseModel, ValidationError

    class _M(BaseModel):
        x: int

    try:
        _M.model_validate({"x": "nope"})
    except ValidationError as exc:
        cls, msg = classify_agent_stream_error(exc)
        assert cls == "llm_output_validation_error"
        assert "validation" in msg.lower()


def test_classify_json_decode_error() -> None:
    import json

    try:
        json.loads("{")
    except json.JSONDecodeError as exc:
        cls, msg = classify_agent_stream_error(exc)
        assert cls == "llm_output_parse_error"
        assert "json" in msg.lower()


def test_classify_internal_error_truncates_long_messages() -> None:
    big = "x" * 500
    cls, msg = classify_agent_stream_error(RuntimeError(big))
    assert cls == "internal_error"
    assert len(msg) <= 200


def test_classify_validation_error_from_string_markers() -> None:
    cls, msg = classify_agent_stream_error(RuntimeError("Validation error in output schema"))
    assert cls == "llm_output_validation_error"
    assert "validation" in msg.lower()


def test_classify_output_parser_error_from_string_markers() -> None:
    cls, msg = classify_agent_stream_error(RuntimeError("Output parser failed to parse content"))
    assert cls == "llm_output_parse_error"
    assert "parse" in msg.lower()
