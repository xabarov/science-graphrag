"""Pure-function phases of the tool execution pipeline (Phase 7.3).

Extracted from ``tool_execution_pipeline.py`` so the LangGraph node closure
stays small and the validation / permission decision logic is unit-testable
without touching ``ToolNode`` or LangGraph state mutations.

Phase boundaries (mirrors ``tool_execution`` debug events):

* :func:`validate_tool_call_batch` — does the latest ``AIMessage`` carry
  any executable ``tool_calls``? Returns either the prepared ``(message,
  tool_calls)`` pair or a typed validation error event.
* :func:`compute_tool_denies` — merges every deny source (tool policy,
  bound surface, plan_mode block list, ``CanUseTool`` callback) into a
  single ``{tool_name: reason}`` dict.

Outputs are plain dicts / dataclasses so the surrounding closure simply
emits debug events / ToolMessages and returns; no module here has any
LangGraph dependency on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage

from science_graphrag.agent.can_use_tool_contract import CanUseTool
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name


@dataclass(frozen=True)
class ValidationFailure:
    """Validation phase rejected the tool batch (no AI message / no tool_calls)."""

    code: str  # ``"no_ai_message"`` | ``"no_tool_calls"``


@dataclass(frozen=True)
class ValidatedToolBatch:
    """The latest ``AIMessage`` carries one or more pending tool_calls."""

    ai_message: AIMessage
    tool_calls: list[Any]


@dataclass(frozen=True)
class DenyDecision:
    """Outcome of the permission phase."""

    denies: dict[str, str] = field(default_factory=dict)

    def is_blocked(self) -> bool:
        """True when at least one tool call is denied."""
        return bool(self.denies)


def validate_tool_call_batch(state: AgentState) -> ValidationFailure | ValidatedToolBatch:
    """Inspect the latest ``AIMessage`` and report whether tool execution can proceed.

    Returns either a :class:`ValidationFailure` with a stable ``code`` (which
    the caller uses for the ``tool_execution`` debug event) or a
    :class:`ValidatedToolBatch` with the message and pending ``tool_calls``.
    """
    msgs = list(state.get("messages") or [])
    last = msgs[-1] if msgs else None
    if not isinstance(last, AIMessage):
        return ValidationFailure(code="no_ai_message")
    tcs = list(getattr(last, "tool_calls", None) or [])
    if not tcs:
        return ValidationFailure(code="no_tool_calls")
    return ValidatedToolBatch(ai_message=last, tool_calls=tcs)


def _policy_denies(*, policy: str, tcs: list[Any]) -> dict[str, str]:
    if policy not in {"no_tools", "clarify"}:
        return {}
    out: dict[str, str] = {}
    for tc in tcs:
        if not isinstance(tc, dict):
            continue
        nm = normalize_tool_call_name(str(tc.get("name") or ""))
        if nm:
            out[nm] = f"tool_policy:{policy}"
    return out


def _surface_denies(
    *, tcs: list[Any], allowed_names: set[str], existing: dict[str, str]
) -> dict[str, str]:
    out: dict[str, str] = {}
    for tc in tcs:
        if not isinstance(tc, dict):
            continue
        nm = normalize_tool_call_name(str(tc.get("name") or ""))
        if not nm:
            continue
        if nm not in allowed_names and nm not in existing:
            out[nm] = "not_in_bound_tool_surface"
    return out


def _bound_denies(
    *, tcs: list[Any], bound: set[str] | None, existing: dict[str, str]
) -> dict[str, str]:
    if not bound:
        return {}
    out: dict[str, str] = {}
    for tc in tcs:
        if not isinstance(tc, dict):
            continue
        nm = normalize_tool_call_name(str(tc.get("name") or ""))
        if nm and nm not in bound and nm not in existing:
            out[nm] = "not_in_bound_tool_surface"
    return out


def _plan_mode_denies(
    *,
    tcs: list[Any],
    plan_mode_active: bool,
    plan_mode_high_risk: set[str],
    existing: dict[str, str],
) -> dict[str, str]:
    if not plan_mode_active or not plan_mode_high_risk:
        return {}
    out: dict[str, str] = {}
    for tc in tcs:
        if not isinstance(tc, dict):
            continue
        nm = normalize_tool_call_name(str(tc.get("name") or ""))
        if nm and nm in plan_mode_high_risk and nm not in existing:
            out[nm] = "plan_mode:high_risk_tool_blocked"
    return out


def _callback_denies(
    *,
    tcs: list[Any],
    can_use_tool: CanUseTool | None,
    state: AgentState,
    existing: dict[str, str],
) -> dict[str, str]:
    if can_use_tool is None:
        return {}
    out: dict[str, str] = {}
    for tc in tcs:
        if not isinstance(tc, dict):
            continue
        nm = normalize_tool_call_name(str(tc.get("name") or ""))
        if not nm or nm in existing or nm in out:
            continue
        try:
            reason = can_use_tool(state, nm, tc)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            out[nm] = f"can_use_tool_callback_error:{type(exc).__name__}"
            continue
        if reason:
            out[nm] = str(reason).strip() or "tool_denied_by_policy"
    return out


def compute_tool_denies(  # pylint: disable=too-many-arguments
    *,
    state: AgentState,
    tcs: list[Any],
    policy: str,
    allowed_names: set[str],
    bound: set[str] | None,
    plan_mode_active: bool,
    plan_mode_high_risk: set[str],
    can_use_tool: CanUseTool | None,
) -> DenyDecision:
    """Aggregate every deny source into a single ``{tool_name: reason}`` map.

    Sources are layered in the order the legacy inline pipeline used:

    1. tool policy (``no_tools`` / ``clarify``)
    2. mode allowlist (``allowed_names``)
    3. bound tool surface (per-turn shortlist)
    4. plan_mode high-risk block list
    5. ``CanUseTool`` callback (last-mile, can also synthesize errors)

    Each layer respects already-recorded reasons (first writer wins) so the
    most specific refusal is preserved across sources.
    """
    if not tcs:
        return DenyDecision({})
    denies: dict[str, str] = {}
    denies.update(_policy_denies(policy=policy, tcs=tcs))
    denies.update(_surface_denies(tcs=tcs, allowed_names=allowed_names, existing=denies))
    denies.update(_bound_denies(tcs=tcs, bound=bound, existing=denies))
    denies.update(
        _plan_mode_denies(
            tcs=tcs,
            plan_mode_active=plan_mode_active,
            plan_mode_high_risk=plan_mode_high_risk,
            existing=denies,
        )
    )
    denies.update(
        _callback_denies(
            tcs=tcs,
            can_use_tool=can_use_tool,
            state=state,
            existing=denies,
        )
    )
    return DenyDecision(denies=denies)


__all__ = [
    "DenyDecision",
    "ValidatedToolBatch",
    "ValidationFailure",
    "compute_tool_denies",
    "validate_tool_call_batch",
]
