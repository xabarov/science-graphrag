"""Optional `agent_note` SSE events: short LLM-generated phrases that explain
what the agent is about to do, similar to Cursor's reasoning stream.

Hard guardrails (intentional):

* Disabled by default (``Settings.agent_note_enabled``); never used in eval
  pipelines or background workers unless the operator opts in.
* Per-event LLM ``max_tokens`` cap (``agent_note_max_tokens``, default 64).
* Per-call wall-clock timeout (``agent_note_timeout_seconds``, default 2.5s);
  on timeout / network failure the note is dropped silently and ``None`` is
  returned so the SSE stream never stalls.
* Output is post-processed: stripped, single line, ≤200 characters.

This module is intentionally independent from ``llm_turn_classifier`` so that
turning notes off does not change classifier behavior.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

from langchain_core.messages import HumanMessage

from science_graphrag.agent.llm.chat import build_chat_model
from science_graphrag.config import Settings

logger = logging.getLogger(__name__)

NoteKind = Literal["intent", "route", "tool"]

_NOTE_PROMPTS: dict[str, str] = {
    "intent": (
        "You narrate the next step of a scholarly research assistant in the user's voice. "
        "Given the user's question and a short interpretation, write ONE sentence (<=140 chars, "
        "no markdown, no quotes, plain prose) describing what you will do FIRST. "
        "Do not invent paper titles or facts; do not mention internal codes."
    ),
    "route": (
        "You narrate the next step of a scholarly research assistant. The supervisor just routed "
        "the task to a specialist. Write ONE sentence (<=140 chars, plain prose) describing the "
        "concrete sub-task you are handing off (e.g. 'Pull recent papers on X', 'Trace citation "
        "graph for author Y'). No internal codes, no markdown."
    ),
    "tool": (
        "You narrate the next step of a scholarly research assistant. A tool just returned data. "
        "Write ONE sentence (<=140 chars, plain prose) describing the next move: skim/filter/look "
        "up details, etc. Do not summarize results, do not invent facts, no markdown."
    ),
}


def _sanitize_note(raw: str) -> str:
    """Trim, single-line, length-cap; reject empty / markdown-only output."""
    text = str(raw or "").strip()
    if not text:
        return ""
    # Collapse internal whitespace / line breaks to single spaces.
    text = " ".join(text.split())
    if text.startswith(("```", "#")):
        return ""
    return text[:200]


def _build_user_block(*, kind: NoteKind, context: dict[str, Any]) -> str:
    parts: list[str] = []
    question = str(context.get("question") or "").strip()
    if question:
        parts.append(f"user_question={question[:600]!r}")
    answer_class = str(context.get("answer_class") or "").strip()
    if answer_class:
        parts.append(f"answer_class={answer_class!r}")
    reason = str(context.get("reason") or "").strip()
    if reason:
        parts.append(f"reason={reason[:200]!r}")
    if kind == "route":
        specialist = str(context.get("specialist") or "").strip()
        if specialist:
            parts.append(f"specialist={specialist!r}")
    if kind == "tool":
        tool = str(context.get("tool") or "").strip()
        if tool:
            parts.append(f"last_tool={tool!r}")
    return "\n".join(parts) or "(no extra context)"


def _generate_note_sync(
    *, kind: NoteKind, context: dict[str, Any], settings: Settings
) -> str | None:
    """Blocking single-shot LLM call. Run inside ``asyncio.to_thread``."""
    api_key = str(settings.extraction_llm_api_key or "").strip()
    if not api_key:
        return None
    if kind not in _NOTE_PROMPTS:
        return None
    try:
        note_model = str(getattr(settings, "agent_note_model_id", "") or "").strip()
        llm = build_chat_model(
            settings,
            temperature=0.2,
            max_tokens=int(settings.agent_note_max_tokens),
            timeout_seconds=float(settings.agent_note_timeout_seconds),
            max_retries=0,
            model=note_model or None,
        )
        messages = [
            HumanMessage(content=_NOTE_PROMPTS[kind]),
            HumanMessage(content=_build_user_block(kind=kind, context=context)),
        ]
        resp = llm.invoke(messages)
    except Exception as exc:  # noqa: BLE001
        logger.debug("agent_note generation failed (kind=%s): %s", kind, exc)
        return None
    content = getattr(resp, "content", "") if resp is not None else ""
    if isinstance(content, list):
        # Some chat models return list[dict|str]. Coerce to a string safely.
        flat: list[str] = []
        for piece in content:
            if isinstance(piece, str):
                flat.append(piece)
            elif isinstance(piece, dict):
                flat.append(str(piece.get("text") or piece.get("content") or ""))
        text = " ".join(s for s in flat if s)
    else:
        text = str(content or "")
    note = _sanitize_note(text)
    return note or None


async def maybe_generate_agent_note(
    *,
    kind: NoteKind,
    context: dict[str, Any],
    settings: Settings,
) -> str | None:
    """Generate one short note; return ``None`` when disabled / on any failure.

    Honors a hard timeout (``agent_note_timeout_seconds``); on timeout the note
    is dropped silently. Never raises — returning ``None`` is the failure
    signal that callers should treat as "no note this step".
    """
    if not bool(getattr(settings, "agent_note_enabled", False)):
        return None
    if not str(getattr(settings, "extraction_llm_api_key", "") or "").strip():
        return None
    timeout = max(0.5, float(getattr(settings, "agent_note_timeout_seconds", 2.5)))
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_generate_note_sync, kind=kind, context=context, settings=settings),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.debug("agent_note generation timed out (kind=%s)", kind)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("agent_note generation raised (kind=%s): %s", kind, exc)
        return None


__all__ = ["maybe_generate_agent_note", "NoteKind"]
