from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, replace
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from science_graphrag.agent.chat_envelope import build_chat_envelope, heuristic_answer_class
from science_graphrag.agent.context.post_turn import apply_turn_digest_to_thread
from science_graphrag.agent.context.session_store import get_session_for_thread
from science_graphrag.agent.graph.invoke_timeout import invoke_graph_with_deadline
from science_graphrag.agent.graph.state import build_initial_agent_state
from science_graphrag.agent.graph.supervisor import build_retrieval_graph
from science_graphrag.agent.graph.tracing import collect_tool_trace
from science_graphrag.agent.trace import ToolCallTrace
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings
from science_graphrag.observability.spans import (
    OpenInferenceAttributes,
    SpanAttributes,
    chain_span,
)
from science_graphrag.observability.spans.decorators import MIME_TYPE_JSON


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


def extract_langgraph_answer(messages: list[Any]) -> tuple[str, list[dict[str, Any]] | None]:
    """Prefer ``final_answer`` tool JSON over a bare assistant string (avoids losing structured output).

    Returns ``(answer, citations_or_none)``. When ``citations_or_none`` is ``None``, keep graph state
    citations; when a list (possibly empty), it replaces citations from ``final_answer`` payload.
    """
    fallback_tool_args: tuple[str, list[dict[str, Any]] | None] | None = None
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if not isinstance(msg, AIMessage):
            continue
        for tc in getattr(msg, "tool_calls", None) or []:
            if str(tc.get("name") or "") != "final_answer":
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
                        return ans.strip(), [c for c in cites if isinstance(c, dict)]
                    return ans.strip(), []
    if fallback_tool_args is not None:
        return fallback_tool_args
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            return str(msg.content or ""), None
    return "", None


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
    evidence_summary: str | None = None
    warnings: list[str] = field(default_factory=list)
    inventory: dict[str, Any] | None = None
    relation_trace: dict[str, Any] | None = None
    quote_candidates: list[dict[str, Any]] | None = None
    idea_suggestions: list[dict[str, Any]] | None = None
    bibliography: dict[str, Any] | None = None
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
    ) -> AgentRunOutput:
        tid = (thread_id or "").strip() or None
        session_id = tid or str(uuid.uuid4())
        attrs: dict[str, Any] = {
            "agent.runtime": self._settings.agent_runtime,
            "agent.max_tool_calls": max_tool_calls or self._settings.agent_max_tool_calls,
            "user.id": workspace_id or "",
            "input.value": question[:500],
            OpenInferenceAttributes.SESSION_ID: session_id,
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
            )

    def _run_langgraph(
        self,
        *,
        question: str,
        workspace_id: str | None,
        max_tool_calls: int,
        answer_class_hint: str | None = None,
        thread_id: str | None = None,
        history_digest: list[dict[str, Any]] | None = None,
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
        )
        assert self._graph is not None
        cfg = {"recursion_limit": self._settings.agent_supervisor_recursion_limit}
        final_state = invoke_graph_with_deadline(
            self._graph,
            initial_state,
            config=cfg,
            timeout_seconds=float(self._settings.agent_step_timeout_seconds),
        )
        messages = list(final_state.get("messages", []))
        trace = collect_tool_trace(final_state)
        answer, fa_citations = extract_langgraph_answer(messages)
        citations = list(final_state.get("citations", []))
        if fa_citations is not None:
            citations = fa_citations
        envelope = build_chat_envelope(
            state=final_state,
            answer=answer,
            citations=citations,
            tool_trace=trace,
            answer_class_hint=answer_class_hint,
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
            _agent_query_output_summary(
                answer_class=ac,
                tool_trace=trace,
                warnings=list(envelope.get("warnings") or []),
                citations=citations,
                routing_log=routing_log,
            ),
            mime_type=MIME_TYPE_JSON,
        )

        return AgentRunOutput(
            answer=answer,
            citations=citations,
            tool_trace=trace,
            answer_class=ac,
            evidence_summary=envelope.get("evidence_summary"),
            warnings=list(envelope.get("warnings") or []),
            inventory=envelope.get("inventory"),
            relation_trace=envelope.get("relation_trace"),
            quote_candidates=envelope.get("quote_candidates"),
            idea_suggestions=envelope.get("idea_suggestions"),
            bibliography=envelope.get("bibliography"),
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
