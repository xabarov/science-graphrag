"""Bounded PDF read cache eviction."""

from __future__ import annotations

from science_graphrag.agent.tools.external.pdf_read_bounded_cache import BoundedTtlPdfReadCache


def test_bounded_cache_evicts_oldest_when_over_cap() -> None:
    c = BoundedTtlPdfReadCache(max_entries=3)
    c.set("a", 300, {"ok": True, "k": "a"})
    c.set("b", 300, {"ok": True, "k": "b"})
    c.set("c", 300, {"ok": True, "k": "c"})
    c.set("d", 300, {"ok": True, "k": "d"})
    assert c.get("a") is None
    hit = c.get("d")
    assert hit is not None
    assert hit.get("k") == "d"
