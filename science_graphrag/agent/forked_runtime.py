"""Cache-safe side-LLM seam (roadmap §10.2).

Side calls (thread insight synthesis, future L4 compact) route through this module so
OpenRouter-style prompt-cache telemetry can be recorded in ``thread_insight_audit`` and
trace-review without duplicating transport logic at each call site.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from science_graphrag.agent.llm.chat import build_chat_model, effective_chat_llm_model
from science_graphrag.config import Settings
from science_graphrag.llm.concurrency import invoke_chat_gated

logger = logging.getLogger(__name__)

_THREAD_INSIGHT_FORK_SYSTEM = (
    "You compress multi-turn research digests into one structured thread insight for the "
    "coordinator. Be factual; do not invent tool results or citations. Output concise "
    "Markdown with headings: ## Themes, ## Open questions, ## Constraints."
)


def side_llm_fork_metadata(
    *,
    forked: bool = False,
    side_llm_cache_read_tokens: int | None = None,
    side_llm_cache_creation_tokens: int | None = None,
    side_llm_cache_read_ratio: float | None = None,
) -> dict[str, Any]:
    """Telemetry fragment for trace-review / audit (thread_insight_audit, L4 audit)."""
    return {
        "forked": bool(forked),
        "side_llm_cache_read_ratio": side_llm_cache_read_ratio,
        "side_llm_cache_creation_tokens": side_llm_cache_creation_tokens,
        "side_llm_cache_read_tokens": side_llm_cache_read_tokens,
    }


def _coerce_int(val: Any) -> int | None:
    if val is None:
        return None
    try:
        n = int(val)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def _cache_tokens_from_usage_metadata(usage: dict[str, Any]) -> tuple[int | None, int | None]:
    """Best-effort (OpenRouter / Anthropic / OpenAI-shaped) cache read vs creation tokens."""
    read_candidates = (
        "cache_read_input_tokens",
        "cache_read_tokens",
        "prompt_cache_read_tokens",
        "cached_prompt_tokens",
    )
    create_candidates = (
        "cache_creation_input_tokens",
        "cache_creation_tokens",
        "prompt_cache_creation_tokens",
    )
    cr: int | None = None
    cc: int | None = None
    for k in read_candidates:
        if k in usage:
            cr = _coerce_int(usage.get(k))
            break
    details = usage.get("input_token_details")
    if cr is None and isinstance(details, dict):
        cr = _coerce_int(details.get("cache_read"))
    for k in create_candidates:
        if k in usage:
            cc = _coerce_int(usage.get(k))
            break
    if cc is None and isinstance(details, dict):
        cc = _coerce_int(details.get("cache_creation") or details.get("ephemeral_5m_input_tokens"))
    return cr, cc


def _cache_tokens_from_ai_message(msg: AIMessage) -> tuple[int | None, int | None]:
    um = getattr(msg, "usage_metadata", None)
    cr: int | None = None
    cc: int | None = None
    if isinstance(um, dict):
        cr, cc = _cache_tokens_from_usage_metadata(um)
    rm = getattr(msg, "response_metadata", None)
    if isinstance(rm, dict):
        tok = rm.get("token_usage")
        if isinstance(tok, dict):
            nested = tok.get("prompt_tokens_details")
            if isinstance(nested, dict) and cr is None:
                cr = _coerce_int(nested.get("cached_tokens"))
        usage = rm.get("usage")
        if isinstance(usage, dict):
            cr2, cc2 = _cache_tokens_from_usage_metadata(usage)
            cr = cr if cr is not None else cr2
            cc = cc if cc is not None else cc2
    return cr, cc


def _cache_read_ratio(cache_read: int | None, cache_creation: int | None) -> float | None:
    """Share of cache-read vs (read+creation) token accounting.

    When the provider reports explicit zeros (e.g. ``cache_read_input_tokens: 0`` with no
    creation field), treat as **0.0** so trace-review can aggregate non-null ratios instead
    of ``fail_missing_side_llm_cache_telemetry``. Unknown = both sides absent.
    """
    if cache_read is None and cache_creation is None:
        return None
    r = int(cache_read or 0)
    c = int(cache_creation or 0)
    denom = r + c
    if denom > 0:
        return round(r / denom, 4)
    return 0.0


@dataclass(frozen=True, slots=True)
class SideLlmRunResult:
    """One side-LLM completion with cache telemetry."""

    text: str
    forked: bool
    latency_ms: int
    side_llm_cache_read_tokens: int | None
    side_llm_cache_creation_tokens: int | None
    side_llm_cache_read_ratio: float | None


def run_side_llm_chat(
    *,
    settings: Settings,
    parent_system: str,
    fork_prompt: str,
    parent_messages_prefix: Sequence[BaseMessage] | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.0,
    pool_name: str = "agent_chat",
) -> SideLlmRunResult:
    """Single chat completion with shared system + optional prefix (cache-key friendly).

    Does not bind tools (thread_insights / side summaries are tool-free). ``forked`` is
    ``True`` when the provider returns an ``AIMessage`` (normal path). Unexpected message
    types are treated as non-fork telemetry (``forked=False``) with best-effort text.
    """
    llm = build_chat_model(
        settings,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
    )
    sys_add_kw: dict[str, Any] = {}
    if bool(getattr(settings, "agent_side_llm_openrouter_cache_control_enabled", False)):
        sys_add_kw["cache_control"] = {"type": "ephemeral"}
    messages: list[BaseMessage] = [
        SystemMessage(content=parent_system, additional_kwargs=sys_add_kw)
    ]
    if parent_messages_prefix:
        messages.extend(list(parent_messages_prefix))
    messages.append(HumanMessage(content=fork_prompt))
    t0 = time.monotonic()
    raw = invoke_chat_gated(llm, messages, pool_name=pool_name, settings=settings)
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    if not isinstance(raw, AIMessage):
        logger.warning("side_llm: unexpected response type %s", type(raw))
        text = str(getattr(raw, "content", "") or "")
        return SideLlmRunResult(
            text=text,
            forked=False,
            latency_ms=elapsed_ms,
            side_llm_cache_read_tokens=None,
            side_llm_cache_creation_tokens=None,
            side_llm_cache_read_ratio=None,
        )
    text = str(raw.content or "").strip()
    cr, cc = _cache_tokens_from_ai_message(raw)
    ratio = _cache_read_ratio(cr, cc)
    return SideLlmRunResult(
        text=text,
        forked=True,
        latency_ms=elapsed_ms,
        side_llm_cache_read_tokens=cr,
        side_llm_cache_creation_tokens=cc,
        side_llm_cache_read_ratio=ratio,
    )


def synthesize_thread_insight_markdown(
    *,
    settings: Settings,
    chunk_summaries: list[str],
    digest_prefix_text: str,
) -> SideLlmRunResult:
    """LLM polish of deterministic chunk summaries into one markdown insight."""
    summaries_block = "\n\n".join(chunk_summaries)
    fork_prompt = (
        "Here are per-chunk digest summaries (deterministic). "
        "Merge them into one thread insight.\n\n"
        f"{summaries_block}"
    )
    prefix_msgs: list[BaseMessage] = []
    blob = (digest_prefix_text or "").strip()
    if blob:
        prefix_msgs.append(
            HumanMessage(
                content=(
                    "Shared digest prefix (verbatim; keep factual alignment with it):\n\n"
                    f"{blob[:12000]}"
                )
            )
        )
    return run_side_llm_chat(
        settings=settings,
        parent_system=_THREAD_INSIGHT_FORK_SYSTEM,
        fork_prompt=fork_prompt,
        parent_messages_prefix=prefix_msgs or None,
        model=effective_chat_llm_model(settings),
        max_tokens=int(getattr(settings, "agent_thread_insights_llm_max_tokens", 768) or 768),
        temperature=float(getattr(settings, "agent_thread_insights_llm_temperature", 0.0) or 0.0),
    )


def run_claim_verification_fork_bundle(**kwargs: Any) -> list[dict[str, Any]]:
    """Side-isolated claim verification runs (tools + deny policy).

    See ``claim_verification_runtime``.
    """
    from science_graphrag.agent.subagents.claim_verification_runtime import (
        run_claim_verification_fanout,
    )

    return run_claim_verification_fanout(**kwargs)


def run_corpus_explore_fork_bundle(**kwargs: Any) -> list[dict[str, Any]]:
    """Fork-bundle entrypoint for corpus_explore fanout."""
    from science_graphrag.agent.subagents.corpus_explore_runtime import run_corpus_explore_fanout

    return run_corpus_explore_fanout(**kwargs)


def run_research_plan_fork_bundle(**kwargs: Any) -> list[dict[str, Any]]:
    """Fork-bundle entrypoint for research-plan fanout."""
    from science_graphrag.agent.subagents.research_plan_runtime import run_research_plan_fanout

    return run_research_plan_fanout(**kwargs)


__all__ = [
    "SideLlmRunResult",
    "run_claim_verification_fork_bundle",
    "run_corpus_explore_fork_bundle",
    "run_research_plan_fork_bundle",
    "run_side_llm_chat",
    "side_llm_fork_metadata",
    "synthesize_thread_insight_markdown",
]
