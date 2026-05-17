"""Answer extraction, salvage paths, and usage aggregation (Wave A runtime seam)."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from science_graphrag.agent.chat_envelope import collect_typed_payloads
from science_graphrag.agent.final_answer_policy import has_completed_final_answer_tool
from science_graphrag.agent.subagent_output_contract import (
    format_salvage_limitation_lines,
    merge_limitation_signals,
)
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name
from science_graphrag.agent.trace import ToolCallTrace

RUNTIME_FALLBACK_ANSWER = (
    "I could not produce a complete final answer for this turn. "
    "Please rephrase the request or narrow the scope."
)


def synthesize_partial_answer_from_specialist_context(
    *,
    citations: list[dict[str, Any]] | None,
    specialist_results_v3: dict[str, Any] | None,
    language: str,
) -> str:
    """Build a deterministic partial answer when terminal synthesis failed but evidence exists."""
    cits = [c for c in list(citations or []) if isinstance(c, dict)]
    sr3 = specialist_results_v3 if isinstance(specialist_results_v3, dict) else {}
    merge = sr3.get("merge") if isinstance(sr3.get("merge"), dict) else {}
    completion_state = str(merge.get("completion_state") or "").strip()
    directive = str(merge.get("writer_directive") or "").strip()
    limitations, next_checks = merge_limitation_signals(merge)
    outcome_summary = str(merge.get("outcome_summary") or "").strip()
    directive_trim = directive[:600] if directive else ""
    limitation_lines = format_salvage_limitation_lines(
        language=language,
        limitations=limitations,
        next_checks=next_checks,
        outcome_summary=outcome_summary,
        writer_directive=directive_trim,
    )
    if language == "ru":
        lines = [
            (
                "Не удалось автоматически завершить полноценный ответ в этом ходе, "
                "но собранные данные сохранены."
            ),
            "Промежуточный результат:",
        ]
        if completion_state:
            lines.append(f"- completion_state: {completion_state}")
        lines.append(f"- получено источников: {len(cits)}")
        lines.extend(limitation_lines)
        lines.append(
            "Рекомендация: продолжить с уже собранными источниками; "
            "текущий вывод ограничен доступной выборкой."
        )
        return "\n".join(lines)
    lines = [
        (
            "The run did not finish a complete final synthesis, "
            "but intermediate evidence was collected."
        ),
        "Partial status:",
    ]
    if completion_state:
        lines.append(f"- completion_state: {completion_state}")
    lines.append(f"- collected sources: {len(cits)}")
    lines.extend(limitation_lines)
    lines.append("Recommendation: continue from the collected evidence; this turn is partial.")
    return "\n".join(lines)


def coerce_optional_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    s = value.strip()
    return s or None


def agent_query_output_summary(
    *,
    answer_class: str,
    tool_trace: list[ToolCallTrace],
    warnings: list[str],
    citations: list[dict[str, Any]],
    routing_log: list[dict[str, Any]] | None,
    budget_exhausted_hint: bool | None = None,
) -> dict[str, Any]:
    routing = routing_log or []
    budget_exhausted = bool(budget_exhausted_hint) or any(
        isinstance(x, dict) and str(x.get("reason") or "") == "budget_exhausted" for x in routing
    )
    return {
        "answer_class": answer_class,
        "tool_call_count": len(tool_trace),
        "warning_codes": [str(w) for w in warnings][:24],
        "citation_count": len(citations),
        "budget_exhausted": budget_exhausted,
    }


_GRAPH_TOOL_SALVAGE_PREFIX = (
    "[Graph tool output; call final_answer to complete the turn for the user.]\n"
)


def _tool_message_payload_dict(msg: ToolMessage) -> dict[str, Any] | None:
    raw = msg.content
    if not isinstance(raw, str):
        return None
    try:
        parsed = json.loads(raw)
    except Exception:  # noqa: BLE001
        return None
    return parsed if isinstance(parsed, dict) else None


def _salvage_answer_from_last_graph_tool(messages: list[Any], *, max_chars: int = 4000) -> str:
    """Build a short user-visible string from the latest ``cypher_query`` / ``edge_search`` JSON."""
    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            continue
        name = normalize_tool_call_name(str(getattr(msg, "name", "") or ""))
        if name not in {"cypher_query", "edge_search"}:
            continue
        data = _tool_message_payload_dict(msg)
        if data is None:
            continue
        if name == "cypher_query":
            err = data.get("error")
            if isinstance(err, str) and err.strip():
                return f"{_GRAPH_TOOL_SALVAGE_PREFIX}Cypher error: {err.strip()[:800]}"
            rows = data.get("rows")
            if not isinstance(rows, list) or not rows:
                continue
            snippet = json.dumps(rows, ensure_ascii=False, default=str)[:max_chars]
            if not snippet.strip():
                continue
            nrows = data.get("row_count", len(rows))
            return (
                f"{_GRAPH_TOOL_SALVAGE_PREFIX}Cypher returned {nrows} row(s). Preview:\n{snippet}"
            )
        items = data.get("items")
        if not isinstance(items, list) or not items:
            continue
        snippet = json.dumps(items, ensure_ascii=False, default=str)[:max_chars]
        if not snippet.strip():
            continue
        return (
            f"{_GRAPH_TOOL_SALVAGE_PREFIX}edge_search returned {len(items)} edge(s). "
            f"Preview:\n{snippet}"
        )
    return ""


_MIN_DRAFT_ASSISTANT_CHARS = 200


def _stringify_ai_message_content(content: Any) -> str:
    """Flatten AIMessage.content (str or provider-specific multimodal lists) for salvage."""
    if isinstance(content, str):
        return content.strip()
    if content is None:
        return ""
    return str(content).strip()


def _salvage_visible_ai_after_defective_final_answer(messages: list[Any]) -> str:
    """Use same-turn AIMessage visible text when ``final_answer`` JSON has an empty ``answer``."""
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if not isinstance(msg, AIMessage):
            continue
        for tc in getattr(msg, "tool_calls", None) or []:
            if normalize_tool_call_name(str(tc.get("name") or "")) != "final_answer":
                continue
            call_id = tc.get("id")
            payload_empty = False
            for follow in messages[i + 1 :]:
                if not isinstance(follow, ToolMessage):
                    continue
                if getattr(follow, "tool_call_id", None) != call_id:
                    continue
                raw = str(follow.content or "").strip()
                if not raw:
                    payload_empty = True
                    break
                try:
                    data = json.loads(raw)
                except Exception:  # noqa: BLE001
                    payload_empty = True
                    break
                if not isinstance(data, dict):
                    payload_empty = True
                    break
                ans = data.get("answer")
                payload_empty = not (isinstance(ans, str) and ans.strip())
                break
            else:
                args = tc.get("args")
                args_dict = args if isinstance(args, dict) else {}
                ans_args = args_dict.get("answer")
                payload_empty = not (isinstance(ans_args, str) and ans_args.strip())
            if not payload_empty:
                continue
            vis = _stringify_ai_message_content(getattr(msg, "content", None))
            if vis:
                return vis[:20_000]
    return ""


def _salvage_substantial_ai_visible_content(messages: list[Any]) -> str:
    """Use substantial ``AIMessage.content`` when ``final_answer`` tool not completed."""
    if has_completed_final_answer_tool(messages):
        return ""
    for msg in reversed(messages):
        if not isinstance(msg, AIMessage):
            continue
        tcs = getattr(msg, "tool_calls", None) or []
        if not tcs:
            continue
        text = str(msg.content or "").strip()
        if len(text) < _MIN_DRAFT_ASSISTANT_CHARS:
            continue
        if text.startswith("{") and text.endswith("}"):
            try:
                json.loads(text)
            except Exception:  # noqa: BLE001
                pass
            else:
                continue
        return text[:20_000]
    return ""


def extract_langgraph_answer(
    messages: list[Any],
) -> tuple[str, list[dict[str, Any]] | None, bool, bool]:
    # pylint: disable=too-many-locals,too-many-branches
    """Prefer ``final_answer`` tool JSON over a bare assistant string.

    Returns ``(answer, citations_or_none, graph_tool_salvage_used, draft_content_salvage)``.
    """
    fallback_tool_args: tuple[str, list[dict[str, Any]] | None] | None = None
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if not isinstance(msg, AIMessage):
            continue
        for tc in getattr(msg, "tool_calls", None) or []:
            if normalize_tool_call_name(str(tc.get("name") or "")) != "final_answer":
                continue
            args = tc.get("args")
            args_dict = args if isinstance(args, dict) else {}
            ans_from_args = args_dict.get("answer")
            if (
                isinstance(ans_from_args, str)
                and ans_from_args.strip()
                and fallback_tool_args is None
            ):
                cites_from_args = args_dict.get("citations")
                fallback_tool_args = (
                    ans_from_args.strip(),
                    (
                        [c for c in cites_from_args if isinstance(c, dict)]
                        if isinstance(cites_from_args, list)
                        else []
                    ),
                )
            call_id = tc.get("id")
            for follow in messages[i + 1 :]:
                if not isinstance(follow, ToolMessage):
                    continue
                if getattr(follow, "tool_call_id", None) != call_id:
                    continue
                raw = follow.content
                if not isinstance(raw, str):
                    continue
                try:
                    data = json.loads(raw)
                except Exception:  # noqa: BLE001
                    continue
                if not isinstance(data, dict):
                    continue
                ans = data.get("answer")
                if isinstance(ans, str) and ans.strip():
                    cites = data.get("citations")
                    if isinstance(cites, list):
                        return ans.strip(), [c for c in cites if isinstance(c, dict)], False, False
                    return ans.strip(), [], False, False
    if fallback_tool_args is not None:
        ans0, cites0 = fallback_tool_args
        return ans0, cites0, False, False
    salvage_def = _salvage_visible_ai_after_defective_final_answer(messages)
    if salvage_def.strip():
        return salvage_def.strip(), None, False, False
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            text = str(msg.content or "").strip()
            if text:
                return text, None, False, False
    salvaged = _salvage_answer_from_last_graph_tool(messages)
    if salvaged.strip():
        return salvaged.strip(), None, True, False
    draft = _salvage_substantial_ai_visible_content(messages)
    if draft.strip():
        return draft.strip(), None, False, True
    return "", None, False, False


def resolve_langgraph_answer_with_salvage(
    final_state: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], bool, bool, bool]:
    """Apply ``extract_langgraph_answer`` then ``salvage_markdown_from_quote_candidates``."""
    messages = list(final_state.get("messages", []))
    answer, fa_citations, graph_salvage, draft_salvage = extract_langgraph_answer(messages)
    quote_salvage = False
    if not (answer or "").strip():
        salv = salvage_markdown_from_quote_candidates(final_state)
        if salv:
            answer = salv
            quote_salvage = True
    citations = list(final_state.get("citations", []))
    if fa_citations is not None:
        citations = list(fa_citations)
    return answer, citations, graph_salvage, quote_salvage, draft_salvage


def salvage_markdown_from_quote_candidates(state: dict[str, Any]) -> str:
    """When ``final_answer`` is missing, surface merged quote candidates as markdown blockquotes."""
    typed = collect_typed_payloads(state)
    rows = typed.get("quote_candidates") or []
    if not isinstance(rows, list) or not rows:
        return ""
    chunks: list[str] = []
    for raw in rows[:8]:
        if not isinstance(raw, dict):
            continue
        text = str(raw.get("quote_text") or raw.get("text") or raw.get("snippet") or "").strip()
        if not text:
            continue
        wid = str(raw.get("work_id") or "").strip()
        head = f"**{wid}**\n\n" if wid else ""
        quoted = "\n".join(f"> {line}" for line in text.splitlines())
        chunks.append(f"{head}{quoted}".strip())
    return "\n\n---\n\n".join(chunks).strip()


def extract_last_brief_from_messages(messages: list[Any]) -> str | None:
    """Return last successful ``brief`` tool text (<=240 chars) if present."""
    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            continue
        if normalize_tool_call_name(str(getattr(msg, "name", "") or "")) != "brief":
            continue
        raw = msg.content
        if not isinstance(raw, str):
            continue
        try:
            data = json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(data, dict) or not data.get("ok"):
            continue
        b = data.get("brief")
        if isinstance(b, str) and b.strip():
            return b.strip()[:240]
    return None


def _coerce_non_negative_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    if n < 0:
        return None
    return n


def _token_triple_from_ai_message(msg: AIMessage) -> tuple[int | None, int | None, int | None]:
    """Return (prompt_tokens, completion_tokens, total_tokens) from LangChain message metadata."""
    prompt = completion = total = None
    usage_meta = getattr(msg, "usage_metadata", None)
    if isinstance(usage_meta, dict):
        prompt = _coerce_non_negative_int(usage_meta.get("input_tokens"))
        if prompt is None:
            prompt = _coerce_non_negative_int(usage_meta.get("prompt_tokens"))
        completion = _coerce_non_negative_int(usage_meta.get("output_tokens"))
        if completion is None:
            completion = _coerce_non_negative_int(usage_meta.get("completion_tokens"))
        total = _coerce_non_negative_int(usage_meta.get("total_tokens"))
    elif usage_meta is not None:
        prompt = _coerce_non_negative_int(getattr(usage_meta, "input_tokens", None))
        if prompt is None:
            prompt = _coerce_non_negative_int(getattr(usage_meta, "prompt_tokens", None))
        completion = _coerce_non_negative_int(getattr(usage_meta, "output_tokens", None))
        if completion is None:
            completion = _coerce_non_negative_int(getattr(usage_meta, "completion_tokens", None))
        total = _coerce_non_negative_int(getattr(usage_meta, "total_tokens", None))
    if prompt is None and completion is None and total is None:
        resp_meta = getattr(msg, "response_metadata", None)
        if isinstance(resp_meta, dict):
            token_usage = resp_meta.get("token_usage")
            if isinstance(token_usage, dict):
                prompt = _coerce_non_negative_int(token_usage.get("prompt_tokens"))
                completion = _coerce_non_negative_int(token_usage.get("completion_tokens"))
                total = _coerce_non_negative_int(token_usage.get("total_tokens"))
    return prompt, completion, total


def aggregate_agent_llm_usage(messages: list[Any]) -> dict[str, int] | None:
    """Sum token usage across ``AIMessage`` nodes (LangGraph state messages)."""
    prompt_sum = 0
    completion_sum = 0
    total_only_sum = 0
    for msg in messages:
        if not isinstance(msg, AIMessage):
            continue
        pt, ct, tt = _token_triple_from_ai_message(msg)
        if pt is None and ct is None and tt is None:
            continue
        parts = int(pt or 0) + int(ct or 0)
        if parts > 0:
            prompt_sum += int(pt or 0)
            completion_sum += int(ct or 0)
        elif tt is not None:
            total_only_sum += int(tt)
    if prompt_sum == 0 and completion_sum == 0 and total_only_sum == 0:
        return None
    combined_total = prompt_sum + completion_sum + total_only_sum
    return {
        "prompt_tokens": prompt_sum,
        "completion_tokens": completion_sum,
        "total_tokens": combined_total,
        "input_tokens": prompt_sum,
        "output_tokens": completion_sum,
    }


__all__ = [
    "RUNTIME_FALLBACK_ANSWER",
    "synthesize_partial_answer_from_specialist_context",
    "agent_query_output_summary",
    "aggregate_agent_llm_usage",
    "coerce_optional_str",
    "extract_langgraph_answer",
    "extract_last_brief_from_messages",
    "resolve_langgraph_answer_with_salvage",
    "salvage_markdown_from_quote_candidates",
]
