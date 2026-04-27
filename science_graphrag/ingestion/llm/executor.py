"""Shared LLM extraction executor with retry and span discipline."""

from __future__ import annotations

import math
import warnings
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

from science_graphrag.ingestion.llm.extractor import EXTRACT_MAYBE_MAX_INNER_ATTEMPTS
from science_graphrag.llm.concurrency import llm_pool_slot
from science_graphrag.observability.phoenix_tracer import SpanAttributes, llm_span
from science_graphrag.utils.llm_deadline import MonotonicDeadline

if TYPE_CHECKING:
    from science_graphrag.config import Settings
    from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)
V = TypeVar("V", bound=BaseModel)

MAX_RETRIES = 2


def _resolve_llm_transport_timeout(
    extractor: "SyncInstructorExtractor",
    *,
    timeout_seconds: float,
    transport_timeout_seconds: float | None,
) -> float:
    """Effective configured transport timeout (warns when legacy args disagree)."""

    if transport_timeout_seconds is not None:
        return float(transport_timeout_seconds)
    if hasattr(extractor, "transport_timeout_seconds"):
        ext_t = float(getattr(extractor, "transport_timeout_seconds"))
        if abs(float(timeout_seconds) - ext_t) > 0.01:
            warnings.warn(
                "run_extraction: pass `transport_timeout_seconds` explicitly; "
                "`timeout_seconds` disagrees with the extractor default and is ignored "
                "for HTTP timeout (extractor transport is used).",
                DeprecationWarning,
                stacklevel=3,
            )
        return ext_t
    warnings.warn(
        "run_extraction: pass `transport_timeout_seconds` explicitly.",
        DeprecationWarning,
        stacklevel=3,
    )
    return float(timeout_seconds)


def run_extraction(  # pylint: disable=too-many-arguments,too-many-locals
    extractor: "SyncInstructorExtractor",
    prompt: str,
    schema: type[T],
    *,
    stage_name: str,
    document_id: str = "",
    source_name: str = "",
    timeout_seconds: float = 60.0,
    transport_timeout_seconds: float | None = None,
    pool_name: str = "ingestion",
    timeout_contract: str = "transport_only",
    operation_deadline_seconds: float | None = None,
    operation_deadline: MonotonicDeadline | None = None,
    response_deadline_seconds: float | None = None,
    system_prompt: str = "",
    retries: int = MAX_RETRIES,
    settings: "Settings | None" = None,
) -> tuple[T | None, str | None]:
    """Execute one extraction call with bounded retries.

    Pass ``transport_timeout_seconds`` explicitly; it is forwarded per HTTP attempt
    (capped by any active ``operation_deadline`` / ``operation_deadline_seconds``).

    Provide either ``operation_deadline`` (shared budget object) or
    ``operation_deadline_seconds`` (wall budget; a new ``MonotonicDeadline`` is created
    when no object is passed).

    When both are set, the object wins for enforcement; ``operation_deadline_seconds``
    should still reflect the same budget for accurate span attributes.
    """

    t_transport = _resolve_llm_transport_timeout(
        extractor,
        timeout_seconds=timeout_seconds,
        transport_timeout_seconds=transport_timeout_seconds,
    )

    op_deadline = operation_deadline or MonotonicDeadline.from_budget_seconds(
        operation_deadline_seconds,
    )
    effective_contract = timeout_contract
    if op_deadline is not None and timeout_contract == "transport_only":
        effective_contract = "transport_with_operation_deadline"

    attempts = max(1, retries + 1)
    last_err: str | None = None
    with llm_pool_slot(pool_name, settings):
        for attempt in range(1, attempts + 1):
            if op_deadline is not None and op_deadline.exhausted():
                return None, "operation_deadline_exceeded"
            rem = op_deadline.remaining() if op_deadline is not None else math.inf
            per_attempt = min(t_transport, rem) if math.isfinite(rem) else t_transport
            if per_attempt <= 0:
                return None, "operation_deadline_exceeded"

            policy = SpanAttributes.llm_runtime_policy_attributes(
                pool_name=pool_name,
                transport_timeout_seconds=t_transport,
                timeout_contract=effective_contract,
                retry_extra_budget=max(0, int(retries)),
                operation_deadline_seconds=operation_deadline_seconds,
                response_deadline_seconds=response_deadline_seconds,
                transport_max_attempts=EXTRACT_MAYBE_MAX_INNER_ATTEMPTS,
            )
            attrs = {
                **policy,
                "document.id": document_id,
                "document.source_name": source_name,
                "extraction.stage": stage_name,
                "extraction.attempt": attempt,
                "extraction.timeout_seconds": per_attempt,
                "llm.per_attempt_transport_timeout_seconds": float(per_attempt),
            }
            with llm_span(f"llm.{stage_name}", attrs):
                parsed, err = extractor.extract_maybe(
                    schema,
                    system=system_prompt,
                    user=prompt,
                    per_attempt_timeout_seconds=per_attempt,
                    operation_deadline=op_deadline,
                )
            if not err and parsed is not None:
                return parsed, None
            if err:
                last_err = err
                if err == "operation_deadline_exceeded":
                    return None, last_err
                continue
            last_err = "llm_empty_result"
    return None, last_err


def run_claims_extraction_with_compact_fallback(  # pylint: disable=too-many-arguments,too-many-locals
    extractor: "SyncInstructorExtractor",
    *,
    primary_user: str,
    primary_system: str,
    primary_schema: type[U],
    compact_user: str,
    compact_system: str,
    compact_schema: type[V],
    document_id: str,
    source_name: str = "",
    timeout_seconds: float = 60.0,
    transport_timeout_seconds: float | None = None,
    operation_deadline_seconds: float | None = None,
    operation_deadline: MonotonicDeadline | None = None,
    retries_primary: int = 0,
    retries_compact: int = 0,
    settings: "Settings | None" = None,
) -> tuple[list[Any], str | None, bool]:
    """
    Try primary claims schema via ``run_extraction``; on failure try compact benchmark schema.

    Primary and compact legs share one operation budget (``operation_deadline`` or derived
    from ``operation_deadline_seconds`` / ``transport``).

    Returns ``(claim_rows, primary_error_if_compact_used, used_compact_fallback)``.
    """

    transport = float(
        transport_timeout_seconds if transport_timeout_seconds is not None else timeout_seconds,
    )
    # Primary + compact legs: default wall budget slightly above two full transports.
    default_span_budget = 2.0 * transport + 5.0
    span_budget = (
        float(operation_deadline_seconds)
        if operation_deadline_seconds is not None
        else default_span_budget
    )
    shared = operation_deadline or MonotonicDeadline.from_budget_seconds(span_budget)
    contract = "transport_with_operation_deadline" if shared is not None else "transport_only"

    parsed_primary, err_primary = run_extraction(
        extractor,
        primary_user,
        primary_schema,
        stage_name="claims_extraction",
        document_id=document_id,
        source_name=source_name,
        timeout_seconds=transport,
        transport_timeout_seconds=transport,
        pool_name="claims",
        timeout_contract=contract,
        operation_deadline_seconds=float(span_budget),
        operation_deadline=shared,
        system_prompt=primary_system,
        retries=retries_primary,
        settings=settings,
    )
    if parsed_primary is not None and not err_primary:
        return list(parsed_primary.claims), None, False

    parsed_compact, err_compact = run_extraction(
        extractor,
        compact_user,
        compact_schema,
        stage_name="claims_extraction_compact",
        document_id=document_id,
        source_name=source_name,
        timeout_seconds=transport,
        transport_timeout_seconds=transport,
        pool_name="claims",
        timeout_contract=contract,
        operation_deadline_seconds=float(span_budget),
        operation_deadline=shared,
        system_prompt=compact_system,
        retries=retries_compact,
        settings=settings,
    )
    if parsed_compact is not None and not err_compact:
        return list(parsed_compact.claims), str(err_primary or "parsed_none"), True

    err_parts = [str(err_primary or "parsed_none")]
    if err_compact:
        err_parts.append(f"compact_fallback_failed: {err_compact}")
    return [], "; ".join(err_parts), False
