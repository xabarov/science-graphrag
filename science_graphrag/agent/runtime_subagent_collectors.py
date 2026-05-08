"""Collect structured HumanMessage payloads from agent transcripts (Wave A seam)."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage


def collect_subagent_task_notifications(messages: list[Any]) -> list[dict[str, Any]]:
    """Extract `task_notification` rows embedded in `HumanMessage.additional_kwargs`."""
    out: list[dict[str, Any]] = []
    for m in messages:
        if not isinstance(m, HumanMessage):
            continue
        ak = getattr(m, "additional_kwargs", None) or {}
        if not isinstance(ak, dict) or ak.get("kind") != "task_notification":
            continue
        inner = ak.get("task_notification")
        if isinstance(inner, dict):
            out.append(inner)
    return out


def collect_claim_verification_results(messages: list[Any]) -> list[dict[str, Any]]:
    """Extract normalized claim-verification child result rows."""
    out: list[dict[str, Any]] = []
    for m in messages:
        if not isinstance(m, HumanMessage):
            continue
        ak = getattr(m, "additional_kwargs", None) or {}
        if not isinstance(ak, dict) or ak.get("kind") != "claim_verification_result":
            continue
        inner = ak.get("claim_verification_result")
        if isinstance(inner, dict):
            out.append(inner)
    return out


def collect_corpus_explore_results(messages: list[Any]) -> list[dict[str, Any]]:
    """Extract normalized corpus-explore child result rows."""
    out: list[dict[str, Any]] = []
    for m in messages:
        if not isinstance(m, HumanMessage):
            continue
        ak = getattr(m, "additional_kwargs", None) or {}
        if not isinstance(ak, dict) or ak.get("kind") != "corpus_explore_result":
            continue
        inner = ak.get("corpus_explore_result")
        if isinstance(inner, dict):
            out.append(inner)
    return out


def collect_research_plan_results(messages: list[Any]) -> list[dict[str, Any]]:
    """Extract normalized research-plan child result rows."""
    out: list[dict[str, Any]] = []
    for m in messages:
        if not isinstance(m, HumanMessage):
            continue
        ak = getattr(m, "additional_kwargs", None) or {}
        if not isinstance(ak, dict) or ak.get("kind") != "research_plan_result":
            continue
        inner = ak.get("research_plan_result")
        if isinstance(inner, dict):
            out.append(inner)
    return out


__all__ = [
    "collect_claim_verification_results",
    "collect_corpus_explore_results",
    "collect_research_plan_results",
    "collect_subagent_task_notifications",
]
