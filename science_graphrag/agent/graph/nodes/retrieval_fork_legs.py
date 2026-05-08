"""Retrieval specialist optional fork bundles (claim verification, corpus explore, research plan)."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage

from science_graphrag.agent.forked_runtime import (
    run_claim_verification_fork_bundle,
    run_corpus_explore_fork_bundle,
    run_research_plan_fork_bundle,
)
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.hooks.subagent_hooks import TerminalState as SubagentHookTerminalState
from science_graphrag.agent.hooks.subagent_hooks import (
    emit_subagent_start_hook,
    emit_subagent_stop_hook,
)
from science_graphrag.agent.subagents.specialist_results_v3 import (
    append_claim_verification_leg,
    append_corpus_explore_leg,
    append_research_plan_leg,
    parse_verdict_from_text,
)
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings


def _hook_terminal_state(term: str) -> SubagentHookTerminalState:
    if term == "timed_out":
        return "timed_out"
    if term == "cancelled":
        return "cancelled"
    if term == "succeeded":
        return "succeeded"
    return "failed"


def run_retrieval_fork_bundles(
    *,
    stores: StoreRegistry,
    settings: Settings,
    state: AgentState,
    question: str,
    new_payloads: list[dict],
    tid: str,
    parent_tid: str,
    sr3: dict[str, Any],
    specialist_results: dict[str, Any],
    meta_out: dict[str, Any],
) -> tuple[list[HumanMessage], list[dict[str, Any]], list[dict[str, Any]]]:
    """Run optional fork legs after retrieval tools; mutates ``specialist_results`` and ``sr3``.

    Returns ``(extra_messages, extra_debug_events, spawn_rows_to_append)``.
    """
    extra_msgs: list[HumanMessage] = []
    extra_debug: list[dict[str, Any]] = []
    spawn_rows: list[dict[str, Any]] = []

    if (
        bool(getattr(settings, "agent_claim_verification_enabled", False))
        and str(settings.agent_runtime or "").strip() == "langgraph_supervisor_v3"
        and new_payloads
    ):
        cv_variants = meta_out.get("claim_verification_variant_suffixes")
        variant_list = (
            [str(x) for x in cv_variants if str(x).strip()]
            if isinstance(cv_variants, list)
            else None
        )
        cv_results = run_claim_verification_fork_bundle(
            stores=stores,
            settings=settings,
            question=question,
            retrieval_payloads=new_payloads,
            workspace_id=state.get("workspace_id"),
            thread_id=tid or None,
            agent_runtime=str(meta_out.get("agent_runtime") or settings.agent_runtime),
            variant_prompt_suffixes=variant_list,
        )
        cv_bucket = list(specialist_results.get("claim_verification") or [])
        working_v3: dict[str, Any] = dict(sr3)
        for cv in cv_results:
            sid = str(cv.get("subagent_id") or "cv-unknown")
            term = str(cv.get("terminal_state") or "failed")
            fc = cv.get("failure_code")
            lat = cv.get("latency_ms")
            hook_local: list[dict[str, Any]] = []
            if parent_tid:
                emit_subagent_start_hook(
                    out=hook_local,
                    subagent_id=sid,
                    parent_turn_id=parent_tid,
                    spawn_reason="claim_verification",
                    leg_kind="spawned",
                    execution_mode="sync",
                )
                emit_subagent_stop_hook(
                    out=hook_local,
                    subagent_id=sid,
                    parent_turn_id=parent_tid,
                    spawn_reason="claim_verification",
                    terminal_state=_hook_terminal_state(term),
                    leg_kind="spawned",
                    latency_ms=int(lat) if isinstance(lat, int) else None,
                    failure_code=str(fc) if fc is not None else None,
                )
                extra_debug.extend(hook_local)
            spawn_rows.append(
                {
                    "subagent_id": sid,
                    "parent_turn_id": parent_tid,
                    "spawn_reason": "claim_verification",
                    "terminal_state": term,
                    "latency_ms": int(lat) if isinstance(lat, int) else None,
                    "failure_code": fc,
                    "tokens": None,
                    "cost_usd_estimate": None,
                    "kind": "spawned",
                }
            )
            working_v3 = append_claim_verification_leg(
                working_v3,
                subagent_id=sid,
                text=str(cv.get("text") or ""),
                terminal_state=term,
                failure_code=str(fc) if fc is not None else None,
                issues=list(cv.get("issues") or []),
                salvage_used=bool(cv.get("salvage_used")),
            )
            verdict = parse_verdict_from_text(str(cv.get("text") or ""))
            cv_bucket.append(
                {
                    "subagent_id": sid,
                    "text": str(cv.get("text") or "")[:8000],
                    "issues": list(cv.get("issues") or [])[:24],
                    "terminal_state": term,
                    "failure_code": fc,
                    "verdict": verdict,
                }
            )
            extra_msgs.append(
                HumanMessage(
                    content="",
                    additional_kwargs={
                        "kind": "claim_verification_result",
                        "claim_verification_result": {
                            "schema_version": 1,
                            "subagent_id": sid,
                            "parent_turn_id": parent_tid or None,
                            "verdict": verdict,
                            "issues": list(cv.get("issues") or [])[:24],
                            "terminal_state": term,
                            "failure_code": fc,
                            "latency_ms": lat,
                        },
                    },
                )
            )
        specialist_results["claim_verification"] = cv_bucket
        sr3.clear()
        sr3.update(working_v3)

    if (
        bool(getattr(settings, "agent_corpus_explore_enabled", False))
        and str(settings.agent_runtime or "").strip() == "langgraph_supervisor_v3"
        and new_payloads
    ):
        ce_results = run_corpus_explore_fork_bundle(
            stores=stores,
            settings=settings,
            question=question,
            retrieval_payloads=new_payloads,
            workspace_id=state.get("workspace_id"),
            thread_id=tid or None,
            agent_runtime=str(meta_out.get("agent_runtime") or settings.agent_runtime),
        )
        ce_bucket = list(specialist_results.get("corpus_explore") or [])
        working_ce = dict(sr3)
        for ce in ce_results:
            sid = str(ce.get("subagent_id") or "ce-unknown")
            term = str(ce.get("terminal_state") or "failed")
            fc = ce.get("failure_code")
            lat = ce.get("latency_ms")
            hook_local_ce: list[dict[str, Any]] = []
            if parent_tid:
                emit_subagent_start_hook(
                    out=hook_local_ce,
                    subagent_id=sid,
                    parent_turn_id=parent_tid,
                    spawn_reason="corpus_explore",
                    leg_kind="spawned",
                    execution_mode="sync",
                )
                emit_subagent_stop_hook(
                    out=hook_local_ce,
                    subagent_id=sid,
                    parent_turn_id=parent_tid,
                    spawn_reason="corpus_explore",
                    terminal_state=_hook_terminal_state(term),
                    leg_kind="spawned",
                    latency_ms=int(lat) if isinstance(lat, int) else None,
                    failure_code=str(fc) if fc is not None else None,
                )
                extra_debug.extend(hook_local_ce)
            spawn_rows.append(
                {
                    "subagent_id": sid,
                    "parent_turn_id": parent_tid,
                    "spawn_reason": "corpus_explore",
                    "terminal_state": term,
                    "latency_ms": int(lat) if isinstance(lat, int) else None,
                    "failure_code": fc,
                    "tokens": None,
                    "cost_usd_estimate": None,
                    "kind": "spawned",
                }
            )
            working_ce = append_corpus_explore_leg(
                working_ce,
                subagent_id=sid,
                text=str(ce.get("text") or ""),
                terminal_state=term,
                failure_code=str(fc) if fc is not None else None,
                issues=list(ce.get("issues") or []),
                salvage_used=bool(ce.get("salvage_used")),
            )
            ce_bucket.append(
                {
                    "subagent_id": sid,
                    "text": str(ce.get("text") or "")[:8000],
                    "issues": list(ce.get("issues") or [])[:24],
                    "terminal_state": term,
                    "failure_code": fc,
                }
            )
            extra_msgs.append(
                HumanMessage(
                    content="",
                    additional_kwargs={
                        "kind": "corpus_explore_result",
                        "corpus_explore_result": {
                            "schema_version": 1,
                            "subagent_id": sid,
                            "parent_turn_id": parent_tid or None,
                            "issues": list(ce.get("issues") or [])[:24],
                            "terminal_state": term,
                            "failure_code": fc,
                            "latency_ms": lat,
                        },
                    },
                )
            )
        specialist_results["corpus_explore"] = ce_bucket
        sr3.clear()
        sr3.update(working_ce)

    if (
        bool(getattr(settings, "agent_research_plan_subagent_enabled", False))
        and str(settings.agent_runtime or "").strip() == "langgraph_supervisor_v3"
        and new_payloads
    ):
        rp_results = run_research_plan_fork_bundle(
            stores=stores,
            settings=settings,
            question=question,
            retrieval_payloads=new_payloads,
            workspace_id=state.get("workspace_id"),
            thread_id=tid or None,
            agent_runtime=str(meta_out.get("agent_runtime") or settings.agent_runtime),
        )
        rp_bucket = list(specialist_results.get("research_plan") or [])
        working_rp = dict(sr3)
        for rp in rp_results:
            sid = str(rp.get("subagent_id") or "rp-unknown")
            term = str(rp.get("terminal_state") or "failed")
            fc = rp.get("failure_code")
            lat = rp.get("latency_ms")
            hook_local_rp: list[dict[str, Any]] = []
            if parent_tid:
                emit_subagent_start_hook(
                    out=hook_local_rp,
                    subagent_id=sid,
                    parent_turn_id=parent_tid,
                    spawn_reason="research_plan",
                    leg_kind="spawned",
                    execution_mode="sync",
                )
                emit_subagent_stop_hook(
                    out=hook_local_rp,
                    subagent_id=sid,
                    parent_turn_id=parent_tid,
                    spawn_reason="research_plan",
                    terminal_state=_hook_terminal_state(term),
                    leg_kind="spawned",
                    latency_ms=int(lat) if isinstance(lat, int) else None,
                    failure_code=str(fc) if fc is not None else None,
                )
                extra_debug.extend(hook_local_rp)
            spawn_rows.append(
                {
                    "subagent_id": sid,
                    "parent_turn_id": parent_tid,
                    "spawn_reason": "research_plan",
                    "terminal_state": term,
                    "latency_ms": int(lat) if isinstance(lat, int) else None,
                    "failure_code": fc,
                    "tokens": None,
                    "cost_usd_estimate": None,
                    "kind": "spawned",
                }
            )
            rw_ok = rp.get("research_plan_write_ok")
            issues_rp = list(rp.get("issues") or [])
            rw_attempted = bool(getattr(settings, "agent_research_plan_tool_enabled", False)) and (
                rw_ok is not None or "research_plan_write_failed" in issues_rp
            )
            working_rp = append_research_plan_leg(
                working_rp,
                subagent_id=sid,
                text=str(rp.get("text") or ""),
                terminal_state=term,
                failure_code=str(fc) if fc is not None else None,
                issues=issues_rp,
                salvage_used=bool(rp.get("salvage_used")),
                research_plan_write_attempted=rw_attempted,
                research_plan_write_ok=rw_ok if isinstance(rw_ok, bool) else None,
            )
            rp_bucket.append(
                {
                    "subagent_id": sid,
                    "text": str(rp.get("text") or "")[:8000],
                    "issues": list(rp.get("issues") or [])[:24],
                    "terminal_state": term,
                    "failure_code": fc,
                    "research_plan_write_ok": rw_ok,
                }
            )
            extra_msgs.append(
                HumanMessage(
                    content="",
                    additional_kwargs={
                        "kind": "research_plan_result",
                        "research_plan_result": {
                            "schema_version": 1,
                            "subagent_id": sid,
                            "parent_turn_id": parent_tid or None,
                            "issues": list(rp.get("issues") or [])[:24],
                            "terminal_state": term,
                            "failure_code": fc,
                            "latency_ms": lat,
                            "research_plan_write_ok": rw_ok,
                        },
                    },
                )
            )
        specialist_results["research_plan"] = rp_bucket
        sr3.clear()
        sr3.update(working_rp)

    return extra_msgs, extra_debug, spawn_rows


__all__ = ["run_retrieval_fork_bundles"]
