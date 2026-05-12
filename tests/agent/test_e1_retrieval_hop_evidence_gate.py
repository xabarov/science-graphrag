"""Unit tests for Wave E1 retrieval-hop evidence gate."""

from __future__ import annotations

from types import SimpleNamespace

from science_graphrag.agent.graph.nodes.retrieval_fork_legs import (
    e1_subagents_allowed_for_retrieval_hop,
)


def test_e1_gate_disabled_allows_single_payload() -> None:
    """When gate is off, a single payload still allows E1 legs."""
    s = SimpleNamespace(
        agent_e1_retrieval_hop_evidence_gate_enabled=False,
        agent_e1_retrieval_hop_min_payloads=2,
    )
    assert e1_subagents_allowed_for_retrieval_hop(settings=s, new_payloads=[{"a": 1}]) is True


def test_e1_gate_requires_min_payloads() -> None:
    """Gate enforces minimum payload count when enabled."""
    s = SimpleNamespace(
        agent_e1_retrieval_hop_evidence_gate_enabled=True,
        agent_e1_retrieval_hop_min_payloads=2,
    )
    assert e1_subagents_allowed_for_retrieval_hop(settings=s, new_payloads=[{"a": 1}]) is False
    assert (
        e1_subagents_allowed_for_retrieval_hop(settings=s, new_payloads=[{"a": 1}, {"b": 2}])
        is True
    )


def test_e1_gate_min_payloads_clamped() -> None:
    """Min payload count is clamped to [1, 10]."""
    s = SimpleNamespace(
        agent_e1_retrieval_hop_evidence_gate_enabled=True,
        agent_e1_retrieval_hop_min_payloads=99,
    )
    assert (
        e1_subagents_allowed_for_retrieval_hop(
            settings=s, new_payloads=[{"x": i} for i in range(10)]
        )
        is True
    )
