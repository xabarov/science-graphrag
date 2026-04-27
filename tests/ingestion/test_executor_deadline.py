"""Phase 1: operation deadline and per-attempt transport enforcement."""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel

from science_graphrag.ingestion.llm.executor import (
    run_claims_extraction_with_compact_fallback,
    run_extraction,
)
from science_graphrag.utils.llm_deadline import MonotonicDeadline


class _Schema(BaseModel):
    value: int = 1


class _DeadlineAwareExtractor:
    transport_timeout_seconds = 60.0
    model = "test/model"
    temperature = 0.0
    max_tokens = 16
    base_url = "https://example.test/v1"

    def __init__(self) -> None:
        self.calls = 0

    def extract_maybe(
        self,
        response_model: type[BaseModel],
        *,
        system: str,
        user: str,
        per_attempt_timeout_seconds: float | None = None,
        operation_deadline: MonotonicDeadline | None = None,
    ) -> tuple[Any, str | None]:
        self.calls += 1
        if operation_deadline is not None:
            if operation_deadline.exhausted():
                return None, "operation_deadline_exceeded"
            time.sleep(min(0.4, max(0.0, operation_deadline.remaining())))
            if operation_deadline.exhausted():
                return None, "operation_deadline_exceeded"
        return None, "forced_fail"


def test_run_extraction_propagates_operation_deadline_exceeded() -> None:
    ext = _DeadlineAwareExtractor()
    deadline = MonotonicDeadline.from_budget_seconds(1.0)
    assert deadline is not None
    parsed, err = run_extraction(
        ext,
        "x",
        _Schema,
        stage_name="metadata_extraction",
        document_id="d1",
        transport_timeout_seconds=30.0,
        pool_name="metadata",
        operation_deadline=deadline,
        operation_deadline_seconds=1.0,
        retries=2,
    )
    assert parsed is None
    assert err == "operation_deadline_exceeded"
    assert ext.calls >= 2


def test_run_claims_compact_skipped_when_deadline_already_exhausted() -> None:
    """Second leg must not run if the shared deadline is exhausted after primary."""

    class _Claims(BaseModel):
        claims: list[Any] = []

    class _Compact(BaseModel):
        claims: list[Any] = []

    class _Extractor:
        transport_timeout_seconds = 30.0
        model = "m"
        temperature = 0.0
        max_tokens = 16
        base_url = "https://example.test/v1"
        calls = 0

        def extract_maybe(
            self,
            response_model: type[BaseModel],
            *,
            system: str,
            user: str,
            per_attempt_timeout_seconds: float | None = None,
            operation_deadline: MonotonicDeadline | None = None,
        ) -> tuple[Any, str | None]:
            self.calls += 1
            if response_model is _Claims:
                if operation_deadline is not None:
                    time.sleep(max(0.0, operation_deadline.remaining() - 0.002))
                return None, "forced_fail"
            if operation_deadline is not None and operation_deadline.exhausted():
                return None, "operation_deadline_exceeded"
            return _Compact(claims=[{"x": 1}]), None

    ext = _Extractor()
    shared = MonotonicDeadline.from_budget_seconds(0.08)
    assert shared is not None
    rows, err, used = run_claims_extraction_with_compact_fallback(
        ext,
        primary_user="p",
        primary_system="s",
        primary_schema=_Claims,
        compact_user="c",
        compact_system="s2",
        compact_schema=_Compact,
        document_id="w1",
        transport_timeout_seconds=30.0,
        operation_deadline=shared,
        operation_deadline_seconds=0.08,
        settings=None,
    )
    assert rows == []
    assert used is False
    assert ext.calls == 1, "compact path should not run after deadline exhausted"
    assert err is not None and "forced_fail" in err


def test_monotonic_deadline_remaining_decreases() -> None:
    d = MonotonicDeadline.from_budget_seconds(0.2)
    assert d is not None
    r0 = d.remaining()
    time.sleep(0.05)
    r1 = d.remaining()
    assert r1 < r0
