"""Epic C3 eval lane identifiers for trace-review / benchmark harnesses."""

from __future__ import annotations

import json
from pathlib import Path

# Canonical lane ids (trace-review: ``run_metadata.eval_lane`` or case ``eval_lane``).
EPIC_C_EVAL_LANES: tuple[str, ...] = (
    "sparse-query",
    "ambiguous_intent",
    "graph-heavy",
    "bibliography-quote",
)


def test_epic_c_eval_lanes_fixture_is_valid_json() -> None:
    """Optional corpus fixture documents the four C3 lanes (offline contract)."""
    path = Path(__file__).resolve().parents[2] / "eval" / "chat_agent" / "epic_c_eval_lanes.v1.json"
    assert path.is_file(), f"missing fixture {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    lanes = data.get("lanes")
    assert isinstance(lanes, list) and len(lanes) == len(EPIC_C_EVAL_LANES)
    ids = {str(x.get("id")) for x in lanes if isinstance(x, dict)}
    assert ids == set(EPIC_C_EVAL_LANES)
