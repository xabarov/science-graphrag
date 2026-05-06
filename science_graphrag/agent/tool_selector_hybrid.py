"""Optional LLM rerank on top of rule-based tool shortlist (Epic C1)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool

from science_graphrag.agent.llm.chat import build_chat_model, ensure_messages_safe_for_generation
from science_graphrag.agent.tool_manifest import ToolManifestEntry, manifest_by_name
from science_graphrag.config import Settings
from science_graphrag.llm.concurrency import invoke_chat_gated

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}")


def _tool_name(t: BaseTool) -> str:
    return str(getattr(t, "name", "") or "").strip()


def _high_risk_allowed(
    name: str,
    *,
    rules_matched: set[str],
    message_merged: set[str],
    carry_merged: set[str],
) -> bool:
    """High-risk tools may enter LLM ranking only when discovery/rules justified them."""
    return name in rules_matched | message_merged | carry_merged


def _pre_llm_candidate_tools(
    picked: list[BaseTool],
    *,
    rules_matched: set[str],
    message_merged: set[str],
    carry_merged: set[str],
    denylist: frozenset[str],
) -> tuple[list[BaseTool], list[str]]:
    """Drop unsafe tools from the LLM candidate pool; return (candidates, denied_names)."""
    by_name = manifest_by_name()
    denied: list[str] = []
    out: list[BaseTool] = []
    for t in picked:
        nm = _tool_name(t)
        if not nm or nm in denylist:
            if nm:
                denied.append(nm)
            continue
        meta = by_name.get(nm)
        if (
            meta
            and meta.risk == "high"
            and not _high_risk_allowed(
                nm,
                rules_matched=rules_matched,
                message_merged=message_merged,
                carry_merged=carry_merged,
            )
        ):
            denied.append(nm)
            continue
        out.append(t)
    return out, denied


def _parse_llm_json(content: str) -> dict[str, Any] | None:
    raw = (content or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = _JSON_BLOCK_RE.search(raw)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None


def _reorder_subset_by_ranked_names(
    base: list[BaseTool],
    ranked: list[str],
    *,
    by_name: dict[str, BaseTool],
) -> list[BaseTool]:
    """Stable merge: LLM order first, then remaining tools from ``base`` only (original order).

    Used so pre-LLM denied / unsafe tools are not re-appended from a wider superset.
    """
    seen: set[str] = set()
    out: list[BaseTool] = []
    for nm in ranked:
        if not nm or nm in seen:
            continue
        hit = by_name.get(nm)
        if hit is None:
            continue
        out.append(hit)
        seen.add(nm)
    for t in base:
        nm = _tool_name(t)
        if nm and nm not in seen:
            out.append(t)
            seen.add(nm)
    return out


def _final_answer_only_from_picked(picked: list[BaseTool]) -> list[BaseTool]:
    """When every tool is pre-filtered out, keep at least ``final_answer`` if present."""
    for t in picked:
        if _tool_name(t) == "final_answer":
            return [t]
    return []


def _picked_in_candidate_order(
    picked: list[BaseTool], candidates: list[BaseTool]
) -> list[BaseTool]:
    """Subset of ``picked`` that appears in ``candidates``, preserving ``picked`` order."""
    want = {_tool_name(t) for t in candidates if _tool_name(t)}
    return [t for t in picked if _tool_name(t) in want]


def maybe_llm_rerank_shortlist(
    picked: list[BaseTool],
    *,
    question: str,
    specialist: str,
    settings: Settings,
    rules_matched_tools: list[str],
    message_discovery_merged: list[str],
    carryover_merged: list[str],
) -> tuple[list[BaseTool], dict[str, Any]]:
    """Optionally rerank ``picked`` with a small JSON-only LLM call.

    Returns ``(picked_out, selector_meta)`` where ``selector_meta`` is merged into
    ``tool_search`` metadata. Pre-LLM denied / disallowed-high-risk tools are removed
    from the returned shortlist (not only from the LLM candidate pool). On LLM failure,
    returns the pre-filtered candidate subset in original ``picked`` order. On empty
    candidates after pre-filter, returns ``final_answer`` only when present in ``picked``.
    """
    meta: dict[str, Any] = {
        "selector_stage": "rules_only",
        "selector_reason_codes": [],
    }
    if not getattr(settings, "agent_tool_search_llm_rerank_enabled", False):
        meta["selector_reason_codes"] = ["llm_rerank_disabled"]
        return picked, meta

    if not picked:
        meta["selector_reason_codes"] = ["llm_rerank_skipped_empty_picked"]
        return picked, meta

    rules_set = {str(x).strip() for x in rules_matched_tools if str(x).strip()}
    msg_set = {str(x).strip() for x in message_discovery_merged if str(x).strip()}
    carry_set = {str(x).strip() for x in carryover_merged if str(x).strip()}
    deny = frozenset(
        str(x).strip()
        for x in (getattr(settings, "agent_tool_search_llm_pre_denylist", None) or [])
        if str(x).strip()
    )

    candidates, pre_denied = _pre_llm_candidate_tools(
        picked,
        rules_matched=rules_set,
        message_merged=msg_set,
        carry_merged=carry_set,
        denylist=deny,
    )
    if pre_denied:
        meta["pre_llm_denied_tools"] = pre_denied

    if not (settings.extraction_llm_api_key or "").strip():
        meta["selector_reason_codes"] = ["llm_rerank_skipped_no_api_key"]
        if not candidates:
            return _final_answer_only_from_picked(picked), meta
        return _picked_in_candidate_order(picked, candidates), meta

    if not candidates:
        meta["selector_reason_codes"] = ["llm_rerank_skipped_empty_candidates"]
        return _final_answer_only_from_picked(picked), meta

    cap = max(4, int(getattr(settings, "agent_tool_search_llm_rerank_max_candidates", 12)))
    capped = candidates[:cap]
    cap_names = [_tool_name(t) for t in capped]
    by_name = {_tool_name(t): t for t in candidates if _tool_name(t)}

    manifest = manifest_by_name()

    def _line(t: BaseTool) -> str:
        nm = _tool_name(t)
        m: ToolManifestEntry | None = manifest.get(nm)
        risk = m.risk if m else "unknown"
        summ = (m.prompt_summary if m else "")[:120]
        return f"- {nm} (risk={risk}, summary={summ})"

    catalog = "\n".join(_line(t) for t in capped)
    sys = (
        "You are a tool-ranking judge for a research assistant. "
        "Pick an ordered subset of tool names that best match the user question. "
        "Output ONLY compact JSON with keys: "
        "ranked_tools (array of strings, subset of candidates, best first), "
        "confidence (number 0..1), "
        "reason_codes (array of short snake_case strings explaining the choice). "
        "You MUST only include names from the candidate list."
    )
    user = (
        f"specialist={specialist}\n"
        f"user_question={question[:4000]}\n"
        f"candidate_tools={json.dumps(cap_names, ensure_ascii=False)}\n"
        f"candidate_catalog:\n{catalog}\n"
    )
    timeout = float(getattr(settings, "agent_tool_search_llm_rerank_timeout_seconds", 8.0))
    max_toks = max(
        64, min(512, int(getattr(settings, "agent_tool_search_llm_rerank_max_tokens", 256)))
    )

    try:
        llm = build_chat_model(settings, max_tokens=max_toks, timeout_seconds=timeout)
        msgs = ensure_messages_safe_for_generation([HumanMessage(content=sys + "\n\n" + user)])
        resp = invoke_chat_gated(
            llm,
            msgs,
            pool_name="agent_chat",
            settings=settings,
        )
        parsed = _parse_llm_json(str(resp.content or ""))
        if not isinstance(parsed, dict):
            raise ValueError("non_object_json")
        ranked = parsed.get("ranked_tools")
        if not isinstance(ranked, list):
            raise ValueError("missing_ranked_tools")
        ranked_strs = [str(x).strip() for x in ranked if str(x).strip()]
        ranked_strs = [x for x in ranked_strs if x in cap_names]
        if not ranked_strs:
            raise ValueError("empty_ranked_after_filter")

        out = _reorder_subset_by_ranked_names(candidates, ranked_strs, by_name=by_name)
        conf_raw = parsed.get("confidence")
        try:
            conf = float(conf_raw) if conf_raw is not None else None
        except (TypeError, ValueError):
            conf = None
        if conf is not None:
            conf = max(0.0, min(1.0, conf))
        rc = parsed.get("reason_codes")
        reason_codes = (
            [str(x).strip() for x in rc if str(x).strip()] if isinstance(rc, list) else []
        )

        meta.update(
            {
                "selector_stage": "hybrid_llm",
                "selector_confidence": conf,
                "selector_reason_codes": reason_codes or ["llm_rerank_ok"],
                "rules_candidate_tools": cap_names,
                "llm_ranked_tools": ranked_strs,
                "pre_llm_denied_tools": pre_denied,
            }
        )
        return out, meta
    except Exception as exc:  # noqa: BLE001
        logger.warning("tool_search llm rerank failed: %s", exc)
        meta.update(
            {
                "selector_stage": "rules_fallback",
                "selector_confidence": None,
                "selector_reason_codes": ["llm_rerank_failed"],
                "pre_llm_denied_tools": pre_denied,
            }
        )
        return _picked_in_candidate_order(picked, candidates), meta


__all__ = ["maybe_llm_rerank_shortlist"]
