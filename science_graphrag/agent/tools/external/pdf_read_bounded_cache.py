"""Bounded in-process TTL cache for PDF read payloads (prevents unbounded growth)."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any


class BoundedTtlPdfReadCache:
    """LRU-ish TTL cache: evict oldest entries when over ``max_entries``."""

    def __init__(self, *, max_entries: int) -> None:
        self._max_entries = max(1, int(max_entries))
        self._lock = threading.Lock()
        self._entries: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()

    def get(self, key: str) -> dict[str, Any] | None:
        now = time.monotonic()
        with self._lock:
            hit = self._entries.get(key)
            if not hit:
                return None
            exp, payload = hit
            if exp < now:
                self._entries.pop(key, None)
                return None
            self._entries.move_to_end(key, last=True)
            return dict(payload)

    def set(self, key: str, ttl_seconds: int, payload: dict[str, Any]) -> None:
        exp = time.monotonic() + float(max(0, int(ttl_seconds)))
        snap = dict(payload)
        with self._lock:
            self._entries[key] = (exp, snap)
            self._entries.move_to_end(key, last=True)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)


_GLOBAL_LOCK = threading.Lock()
_GLOBAL_CACHE: BoundedTtlPdfReadCache | None = None


def get_pdf_read_cache(*, max_entries: int) -> BoundedTtlPdfReadCache:
    """Return process-global cache sized from current settings (rebuilt if cap changes)."""
    global _GLOBAL_CACHE  # noqa: PLW0603
    cap = max(1, int(max_entries))
    with _GLOBAL_LOCK:
        if _GLOBAL_CACHE is None or _GLOBAL_CACHE._max_entries != cap:  # noqa: SLF001
            _GLOBAL_CACHE = BoundedTtlPdfReadCache(max_entries=cap)
        return _GLOBAL_CACHE


__all__ = ["BoundedTtlPdfReadCache", "get_pdf_read_cache"]
