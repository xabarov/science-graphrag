"""Coerce persisted JSON booleans (hand-edited stores may use strings or 0/1)."""

from __future__ import annotations

from typing import Any

_INT_BOOL = {0: False, 1: True}
_STR_BOOL = {
    "true": True,
    "1": True,
    "yes": True,
    "on": True,
    "false": False,
    "0": False,
    "no": False,
    "off": False,
}


def optional_stored_bool(raw: Any) -> bool | None:
    """Return ``True``/``False`` when ``raw`` is a recognizable boolean-ish value.

    Returns ``None`` when the value is missing, empty, or not coercible (do not merge).
    """
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, int):
        return _INT_BOOL.get(raw)
    if isinstance(raw, str):
        return _STR_BOOL.get(raw.strip().lower())
    return None
