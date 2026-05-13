"""Optional per-turn agent_note SSE events."""

from __future__ import annotations

import json
from typing import Any

from science_graphrag.agent.notes import maybe_generate_agent_note
from science_graphrag.config import Settings


async def emit_agent_note(
    *,
    kind: str,
    context: dict[str, Any],
    settings: Settings,
    counter: dict[str, int],
) -> dict[str, str] | None:
    """Generate (if enabled and within budget) and serialize a single agent_note SSE event."""
    if not bool(getattr(settings, "agent_note_enabled", False)):
        return None
    cap = int(getattr(settings, "agent_note_max_per_turn", 0) or 0)
    if cap <= 0:
        return None
    if counter.get("emitted", 0) >= cap:
        return None

    note = await maybe_generate_agent_note(kind=kind, context=context, settings=settings)
    if not note:
        return None
    counter["emitted"] = counter.get("emitted", 0) + 1
    return {"data": json.dumps({"type": "agent_note", "kind": kind, "note": note})}


__all__ = ["emit_agent_note"]
