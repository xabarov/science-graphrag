"""Reader-view authorship meta helpers (debug classification, raw-view property strip)."""

from __future__ import annotations

from typing import Any

from science_graphrag.api.graph_reader_projection.constants import READER_SYNTHETIC_AUTHOR_ID_PREFIX


def compute_authorship_projection_meta(
    center_work_id: str,
    edges: list[dict[str, Any]],
) -> str:
    """Classify reader-view authorship targets linked from the center work.

    Used for optional debug ``meta`` on ``GET /v1/works/{id}/graph`` (no PII).

    Returns one of: ``native``, ``synthesized``, ``mixed``, ``none``.
    ``native`` means every resolved target id from center ``AUTHORED`` edges is
    non-surrogate (does not use the synthetic author id prefix). ``synthesized`` means at
    least one synthetic target and no other native ids on those edges. ``mixed``
    is both. ``none`` is no ``AUTHORED`` edges from the center.
    """
    has_native = False
    has_synth = False
    for edge in edges or []:
        if str(edge.get("type") or "").upper() != "AUTHORED":
            continue
        src_id = str(edge.get("source") or "")
        tgt_id = str(edge.get("target") or "")
        if src_id == center_work_id:
            aid = tgt_id
        elif tgt_id == center_work_id:
            aid = src_id
        else:
            continue
        if not aid:
            continue
        if aid.startswith(READER_SYNTHETIC_AUTHOR_ID_PREFIX):
            has_synth = True
        else:
            has_native = True
    if has_native and has_synth:
        return "mixed"
    if has_native:
        return "native"
    if has_synth:
        return "synthesized"
    return "none"


def strip_reader_only_authorship_properties(nodes: list[dict[str, Any]]) -> None:
    """Drop reader-collapse-only keys from Authorship so ``view=raw`` stays topology-shaped."""
    for n in nodes:
        if str(n.get("type") or "") != "Authorship":
            continue
        props = n.get("properties")
        if not isinstance(props, dict) or "author_entity_id" not in props:
            continue
        n["properties"] = {k: v for k, v in props.items() if k != "author_entity_id"}
