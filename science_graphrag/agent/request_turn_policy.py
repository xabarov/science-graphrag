"""Per-request agent controls (external HTTP research toggle, plan mode, server time hints)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from science_graphrag.agent.context.research_plan_session import (
    reset_research_plan_for_explicit_arxiv_followup,
    reset_research_plan_for_explicit_web_followup,
    seed_research_plan_if_empty,
)
from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.agent.pdf_read_contract import PDF_READ_USER_MESSAGE_TOKEN
from science_graphrag.config import Settings
from science_graphrag.external_intent_markers import (
    ARXIV_MARKERS,
    WEB_FOLLOWUP_INTENT_MARKERS,
)

EXTERNAL_RESEARCH_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "web_search",
        "web_fetch",
        "arxiv_search",
        "arxiv_fetch",
        "unpaywall_lookup",
        "openalex_works_search",
        "semantic_scholar_search",
        "semantic_scholar_paper",
        "read_external_pdf",
    }
)
# External HTTP tools denied when the user disables web research (PDF is gated separately).
EXTERNAL_RESEARCH_WEB_TOOL_NAMES: frozenset[str] = frozenset(
    EXTERNAL_RESEARCH_TOOL_NAMES - frozenset({"read_external_pdf"})
)
WEB_RESEARCH_TOOL_NAMES: frozenset[str] = EXTERNAL_RESEARCH_TOOL_NAMES

AgentUiMode = Literal["agent", "plan"]


@dataclass(frozen=True)
class AgentRequestTurnContext:
    """Resolved per-request tool/session policy for one agent turn."""

    mode: str
    warn_req: list[str]
    turn_tool_denylist: list[str]
    run_metadata_fragment: dict[str, Any]


def _asks_for_web_followup(question: str | None) -> bool:
    q = " ".join(str(question or "").strip().lower().split())
    if not q:
        return False
    return any(marker in q for marker in WEB_FOLLOWUP_INTENT_MARKERS)


def _asks_for_arxiv_followup(question: str | None) -> bool:
    q = " ".join(str(question or "").strip().lower().split())
    if not q:
        return False
    return any(marker in q for marker in ARXIV_MARKERS)


def build_agent_request_turn_context(
    settings: Settings,
    *,
    thread_id: str | None,
    question: str | None = None,
    web_research_enabled: bool | None,
    agent_mode: str,
    pdf_read_request: dict[str, Any] | None = None,
) -> AgentRequestTurnContext:
    """Apply session plan_mode start-of-turn + compute denylist and transparency metadata."""
    mode = (agent_mode or "agent").strip().lower()
    if mode not in {"agent", "plan"}:
        mode = "agent"
    warn_req = list(apply_plan_mode_thread_start(thread_id, mode))
    if mode == "plan":
        seed_research_plan_if_empty(thread_id, question=question)
    if mode == "agent" and _asks_for_arxiv_followup(question):
        reset_research_plan_for_explicit_arxiv_followup(
            thread_id,
            question=question,
        )
    elif mode == "agent" and _asks_for_web_followup(question):
        reset_research_plan_for_explicit_web_followup(
            thread_id,
            question=question,
        )
    user_web = effective_web_research_user_enabled(
        web_research_enabled,
        default_when_unspecified=bool(settings.external_research_default_enabled),
    )
    warn_req.extend(compute_request_warnings(settings, web_research_user_enabled=user_web))
    explicit_pdf = bool(
        isinstance(pdf_read_request, dict) and str(pdf_read_request.get("pdf_url") or "").strip()
    )
    q_raw = str(question or "").strip()
    explicit_pdf_only_turn = explicit_pdf and (
        not q_raw or q_raw == PDF_READ_USER_MESSAGE_TOKEN or q_raw == "[pdf-read-action]"
    )
    tdl = compute_turn_tool_denylist(
        settings,
        web_research_user_enabled=user_web,
        explicit_pdf_read_request=explicit_pdf,
        explicit_pdf_only_turn=explicit_pdf_only_turn,
    )
    frag = build_request_run_metadata_fragment(
        settings,
        web_research_enabled=web_research_enabled,
        agent_mode=mode,
        turn_tool_denylist=tdl,
        request_warnings=warn_req,
        external_research_default_enabled=bool(settings.external_research_default_enabled),
        request_pdf_reading_mode=str(getattr(settings, "pdf_reading_mode", "ask") or "ask"),
    )
    return AgentRequestTurnContext(
        mode=mode,
        warn_req=warn_req,
        turn_tool_denylist=tdl,
        run_metadata_fragment=frag,
    )


def utc_now_iso_z() -> str:
    """Return current UTC time as ISO-8601 with Z suffix (stable for prompts)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def effective_web_research_user_enabled(
    web_research_enabled: bool | None,
    *,
    default_when_unspecified: bool = True,
) -> bool:
    """Resolve per-request external research toggle.

    When ``web_research_enabled`` is ``None``, use ``default_when_unspecified`` (persisted
    operator default via ``Settings.external_research_default_enabled`` at call sites).
    """
    if web_research_enabled is not None:
        return bool(web_research_enabled)
    return bool(default_when_unspecified)


def compute_turn_tool_denylist(
    settings: Settings,
    *,
    web_research_user_enabled: bool,
    explicit_pdf_read_request: bool = False,
    explicit_pdf_only_turn: bool = False,
) -> list[str]:
    """Compute per-turn tool denylist (web research toggle + PDF policy + operator gates)."""
    deny: set[str] = set()
    if explicit_pdf_only_turn:
        deny.update(EXTERNAL_RESEARCH_WEB_TOOL_NAMES)
    if not web_research_user_enabled:
        deny.update(EXTERNAL_RESEARCH_WEB_TOOL_NAMES)
        if not explicit_pdf_read_request:
            deny.add("read_external_pdf")
    if not bool(getattr(settings, "agent_pdf_read_tool_enabled", True)):
        deny.add("read_external_pdf")
    pdf_mode = str(getattr(settings, "pdf_reading_mode", "ask") or "ask").strip().lower()
    if pdf_mode == "off" and not explicit_pdf_read_request:
        deny.add("read_external_pdf")
    return sorted(deny)


def compute_request_warnings(
    settings: Settings,
    *,
    web_research_user_enabled: bool,
) -> list[str]:
    """Request warnings (reserved for future per-turn policy hints)."""
    _ = settings
    _ = web_research_user_enabled
    return []


def apply_plan_mode_thread_start(
    thread_id: str | None,
    agent_mode: str,
) -> list[str]:
    """Sync session_meta.plan_mode with UI agent_mode at turn start.

    Returns warnings (e.g. plan mode requested without thread_id).
    """
    warnings: list[str] = []
    tid = (thread_id or "").strip() or None
    mode = (agent_mode or "agent").strip().lower()
    if mode not in {"agent", "plan"}:
        mode = "agent"
    if not tid:
        if mode == "plan":
            warnings.append("plan_mode_requires_thread_id")
        return warnings
    be = get_session_memory_backend()
    if mode == "plan":
        payload = {
            "active": True,
            "entered_at": time.time(),
            "note": "request_agent_mode_plan",
        }
        be.patch_session_meta(tid, patch={"plan_mode": payload})
    else:
        payload = {
            "active": False,
            "exited_at": time.time(),
            "approved": True,
            "reason": "request_agent_mode_agent",
        }
        be.patch_session_meta(tid, patch={"plan_mode": payload})
    return warnings


def clear_plan_mode_after_plan_turn(thread_id: str | None, *, requested_plan: bool) -> None:
    """Exit request-scoped plan mode after a plan-mode turn completes."""
    if not requested_plan:
        return
    tid = (thread_id or "").strip() or None
    if not tid:
        return
    payload = {
        "active": False,
        "exited_at": time.time(),
        "approved": True,
        "reason": "request_agent_mode_plan_completed",
    }
    get_session_memory_backend().patch_session_meta(tid, patch={"plan_mode": payload})


def build_request_run_metadata_fragment(
    settings: Settings,
    *,
    web_research_enabled: bool | None,
    agent_mode: str,
    turn_tool_denylist: list[str],
    request_warnings: list[str],
    external_research_default_enabled: bool = True,
    request_pdf_reading_mode: str | None = None,
) -> dict[str, Any]:
    """Small fragment merged into run_metadata for UI transparency."""
    user_on = effective_web_research_user_enabled(
        web_research_enabled,
        default_when_unspecified=bool(external_research_default_enabled),
    )
    _b = str(getattr(settings, "agent_pdf_read_backend_mode", "hybrid") or "hybrid").strip().lower()
    if _b not in {"pypdf", "vl", "hybrid"}:
        _b = "hybrid"
    out: dict[str, Any] = {
        "request_web_research_enabled": web_research_enabled,
        "effective_web_research_user_enabled": user_on,
        "effective_web_research_tools": bool(user_on),
        "request_agent_mode": (agent_mode or "agent").strip().lower(),
        "turn_tool_denylist": list(turn_tool_denylist),
        "request_turn_warnings": list(request_warnings),
        "agent_pdf_read_backend_mode": _b,
    }
    if request_pdf_reading_mode:
        out["request_pdf_reading_mode"] = str(request_pdf_reading_mode).strip().lower()
    return out


__all__ = [
    "EXTERNAL_RESEARCH_TOOL_NAMES",
    "EXTERNAL_RESEARCH_WEB_TOOL_NAMES",
    "WEB_RESEARCH_TOOL_NAMES",
    "AgentRequestTurnContext",
    "AgentUiMode",
    "apply_plan_mode_thread_start",
    "build_agent_request_turn_context",
    "build_request_run_metadata_fragment",
    "clear_plan_mode_after_plan_turn",
    "compute_request_warnings",
    "compute_turn_tool_denylist",
    "effective_web_research_user_enabled",
    "utc_now_iso_z",
]
