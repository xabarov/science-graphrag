"""Deterministic edge ids for graph JSON payloads."""

from __future__ import annotations

import hashlib


def stable_graph_edge_id(source: str, rel_type: str, target: str, seq: int) -> str:
    """Return a stable opaque id for an edge (used by authorship collapse and aggregators)."""
    payload = f"{source}\0{rel_type or ''}\0{target}\0{seq}".encode()
    return "e_" + hashlib.sha256(payload).hexdigest()[:22]
