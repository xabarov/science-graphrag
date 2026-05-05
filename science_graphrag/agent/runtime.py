from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, replace
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from science_graphrag.agent.chat_envelope import (
    build_chat_envelope,
    collect_typed_payloads,
    heuristic_answer_class,
)
from science_graphrag.agent.context.post_turn import apply_turn_digest_to_thread
from science_graphrag.agent.context.session_store import get_session_for_thread
from science_graphrag.agent.final_answer_policy import has_completed_final_answer_tool
from science_graphrag.agent.graph.invoke_timeout import invoke_graph_with_deadline
from science_graphrag.agent.graph.state import build_initial_agent_state
from science_graphrag.agent.graph.supervisor import build_retrieval_graph
from science_graphrag.agent.graph.tracing import collect_tool_trace
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name
from science_graphrag.agent.trace import ToolCallTrace
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings
from science_graphrag.observability.spans import (
    OpenInferenceAttributes,
    SpanAttributes,
    add_span_event,
    chain_span,
)
from science_graphrag.observability.spans.decorators import MIME_TYPE_JSON


def _coerce_optional_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    s = value.strip()
    return s or None


def _agent_query_output_summary(
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


def _salvage_substantial_ai_visible_content(messages: list[Any]) -> str:
    """Use long ``AIMessage.content`` left alongside ``tool_calls`` (no completed ``final_answer``)."""
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
    ``citations_or_none`` is ``None`` when citations should come from graph state; otherwise it
    replaces envelope citations from the ``final_answer`` payload. ``graph_tool_salvage_used`` is
    True when ``answer`` was built from ``cypher_query`` / ``edge_search`` JSON. The fourth flag is
    True when ``answer`` was taken from substantial visible ``AIMessage.content`` while tool calls
    were still present (no completed ``final_answer``).
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
    """Apply ``extract_langgraph_answer`` then ``salvage_markdown_from_quote_candidates``.

    Returns ``(answer, citations, graph_salvage, quote_salvage, draft_salvage)``.
    """

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
    """Sum token usage across ``AIMessage`` nodes (LangGraph state messages).

    OpenAI-shaped keys are included for API clients; ``input_tokens`` / ``output_tokens`` mirror
    LangChain ``usage_metadata`` naming for the UI extractor.
    """

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


def current_otel_trace_id_hex() -> str | None:
    try:
        from opentelemetry import trace as trace_api
    except Exception:  # noqa: BLE001
        return None
    sc = trace_api.get_current_span().get_span_context()
    if sc.is_valid:
        return format(sc.trace_id, "032x")
    return None


@dataclass
class AgentRunOutput:
    answer: str
    citations: list[dict[str, Any]]
    tool_trace: list[ToolCallTrace]
    answer_class: str = "grounded_explanation"
    product_path: str | None = None
    product_markers: list[str] = field(default_factory=list)
    evidence_summary: str | None = None
    warnings: list[str] = field(default_factory=list)
    inventory: dict[str, Any] | None = None
    relation_trace: dict[str, Any] | None = None
    quote_candidates: list[dict[str, Any]] | None = None
    idea_suggestions: list[dict[str, Any]] | None = None
    bibliography: dict[str, Any] | None = None
    llm_usage: dict[str, int] | None = None
    debug_events: list[dict[str, Any]] = field(default_factory=list)
    phoenix_trace_id: str | None = None
    thread_id: str | None = None


class RetrievalAgent:
    """Production retrieval agent runtime (Wave Y2: LangGraph ReAct)."""

    def __init__(
        self,
        *,
        settings: Settings,
        stores: StoreRegistry,
    ) -> None:
        self._settings = settings
        self._stores = stores
        if settings.agent_runtime == "retrieval_v1":
            from science_graphrag.agent.runtime_legacy import LegacyRetrievalAgent

            self._legacy = LegacyRetrievalAgent(
                settings=settings,
                neo4j=stores.neo4j,
                chunks=stores.qdrant_chunks,
                works=stores.qdrant_works,
            )
            self._graph = None
        else:
            self._legacy = None
            self._graph = build_retrieval_graph(stores, settings)

    def run(
        self,
        *,
        question: str,
        workspace_id: str | None,
        max_tool_calls: int,
        answer_class_hint: str | None = None,
        thread_id: str | None = None,
        history_digest: list[dict[str, Any]] | None = None,
        client_idle_ms: int | None = None,
    ) -> AgentRunOutput:
        tid = (thread_id or "").strip() or None
        session_id = tid or str(uuid.uuid4())
        deadline_s = float(self._settings.agent_step_timeout_seconds)
        attrs: dict[str, Any] = {
            "agent.runtime": self._settings.agent_runtime,
            "agent.max_tool_calls": max_tool_calls or self._settings.agent_max_tool_calls,
            "user.id": workspace_id or "",
            "input.value": question[:500],
            OpenInferenceAttributes.SESSION_ID: session_id,
            "agent.response_deadline_seconds": deadline_s,
            "agent.response_deadline_enforces_upstream_cancel": False,
        }
        if answer_class_hint:
            attrs["agent.answer_class_hint"] = str(answer_class_hint)[:120]
        if not tid:
            attrs["metadata.agent.request_id"] = session_id
        with chain_span("agent.query", attrs):
            if self._legacy is not None:
                out = self._legacy.run(
                    question=question,
                    workspace_id=workspace_id,
                    max_tool_calls=max_tool_calls,
                )
                out = replace(
                    out,
                    phoenix_trace_id=current_otel_trace_id_hex(),
                    thread_id=tid,
                )
                SpanAttributes.set_output(
                    _agent_query_output_summary(
                        answer_class=out.answer_class,
                        tool_trace=list(out.tool_trace or []),
                        warnings=list(out.warnings or []),
                        citations=list(out.citations or []),
                        routing_log=None,
                    ),
                    mime_type=MIME_TYPE_JSON,
                )
                if tid:
                    ac = heuristic_answer_class(question, answer_class_hint)
                    apply_turn_digest_to_thread(
                        thread_id=tid,
                        raw_user_question=question,
                        answer=out.answer,
                        answer_class=ac,
                        tool_trace=list(out.tool_trace or []),
                        workspace_id=workspace_id,
                    )
                return out
            return self._run_langgraph(
                question=question,
                workspace_id=workspace_id,
                max_tool_calls=max_tool_calls,
                answer_class_hint=answer_class_hint,
                thread_id=tid,
                history_digest=history_digest,
                client_idle_ms=client_idle_ms,
            )

    def _run_langgraph(  # pylint: disable=too-many-locals
        self,
        *,
        question: str,
        workspace_id: str | None,
        max_tool_calls: int,
        answer_class_hint: str | None = None,
        thread_id: str | None = None,
        history_digest: list[dict[str, Any]] | None = None,
        client_idle_ms: int | None = None,
    ) -> AgentRunOutput:
        budget = max_tool_calls or self._settings.agent_max_tool_calls
        session_summary = ""
        if thread_id:
            session_summary = str(get_session_for_thread(thread_id).get("session_summary") or "")

        initial_state = build_initial_agent_state(
            question=question,
            workspace_id=workspace_id,
            max_tool_calls=budget,
            agent_runtime=self._settings.agent_runtime,
            thread_id=thread_id,
            history_digest=history_digest,
            session_summary=session_summary,
            answer_class_hint=answer_class_hint,
            client_idle_ms=client_idle_ms,
            settings=self._settings,
        )
        assert self._graph is not None
        cfg = {"recursion_limit": self._settings.agent_supervisor_recursion_limit}
        final_state = invoke_graph_with_deadline(
            self._graph,
            initial_state,
            config=cfg,
            timeout_seconds=float(self._settings.agent_step_timeout_seconds),
            settings=self._settings,
        )
        messages = list(final_state.get("messages", []))
        llm_usage = aggregate_agent_llm_usage(messages)
        trace = collect_tool_trace(final_state)
        answer, citations, graph_salvage, quote_salvage, draft_salvage = (
            resolve_langgraph_answer_with_salvage(final_state)
        )
        extra_warn_list: list[str] = []
        if graph_salvage:
            extra_warn_list.append("answer_salvaged_from_graph_tool")
        if quote_salvage:
            extra_warn_list.append("answer_salvaged_from_quote_candidates")
        if draft_salvage:
            extra_warn_list.append("answer_salvaged_from_assistant_draft")
        extra_warn: list[str] | None = extra_warn_list or None
        if graph_salvage:
            add_span_event(
                "agent.graph_tool_answer_salvage",
                {"answer_chars": len(answer or "")},
            )
        if quote_salvage:
            add_span_event(
                "agent.quote_candidate_answer_salvage",
                {"answer_chars": len(answer or "")},
            )
        if draft_salvage:
            add_span_event(
                "agent.assistant_draft_answer_salvage",
                {"answer_chars": len(answer or "")},
            )
        envelope = build_chat_envelope(
            state=final_state,
            answer=answer,
            citations=citations,
            tool_trace=trace,
            answer_class_hint=answer_class_hint,
            extra_warnings=extra_warn,
        )
        raw_q = (final_state.get("metadata") or {}).get("raw_user_question")
        if not isinstance(raw_q, str) or not raw_q.strip():
            raw_q = question
        if thread_id:
            apply_turn_digest_to_thread(
                thread_id=thread_id,
                raw_user_question=raw_q,
                answer=answer,
                answer_class=str(envelope.get("answer_class") or "grounded_explanation"),
                tool_trace=trace,
                workspace_id=workspace_id,
            )

        ac = str(envelope.get("answer_class") or "grounded_explanation")
        raw_routing = final_state.get("routing_log")
        routing_log: list[dict[str, Any]] = (
            [x for x in raw_routing if isinstance(x, dict)] if isinstance(raw_routing, list) else []
        )

        SpanAttributes.set_output(
            {
                **_agent_query_output_summary(
                    answer_class=ac,
                    tool_trace=trace,
                    warnings=list(envelope.get("warnings") or []),
                    citations=citations,
                    routing_log=routing_log,
                ),
                "product_path": envelope.get("product_path"),
                "product_markers": list(envelope.get("product_markers") or []),
            },
            mime_type=MIME_TYPE_JSON,
        )

        return AgentRunOutput(
            answer=answer,
            citations=citations,
            tool_trace=trace,
            answer_class=ac,
            product_path=_coerce_optional_str(envelope.get("product_path")),
            product_markers=[
                str(x) for x in (envelope.get("product_markers") or []) if str(x).strip()
            ],
            evidence_summary=envelope.get("evidence_summary"),
            warnings=list(envelope.get("warnings") or []),
            inventory=envelope.get("inventory"),
            relation_trace=envelope.get("relation_trace"),
            quote_candidates=envelope.get("quote_candidates"),
            idea_suggestions=envelope.get("idea_suggestions"),
            bibliography=envelope.get("bibliography"),
            llm_usage=llm_usage,
            debug_events=list(final_state.get("debug_events") or []),
            phoenix_trace_id=current_otel_trace_id_hex(),
            thread_id=thread_id,
        )


def build_agent(
    *,
    settings: Settings,
    stores: StoreRegistry,
) -> RetrievalAgent:
    return RetrievalAgent(settings=settings, stores=stores)
