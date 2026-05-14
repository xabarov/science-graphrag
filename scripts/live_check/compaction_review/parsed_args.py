"""Shared ``Protocol`` for compaction CLI args (turn executor + main runner)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class CompactionParsedArgs(Protocol):  # pylint: disable=too-few-public-methods
    """CLI namespace shape after ``argparse`` (``compaction_turn_review`` entrypoint)."""

    base_url: str
    workspace_id: str | None
    turns: int
    require_compaction_after: int
    timeout: float
    out_json: Path
    out_md: Path
    emit_merged_into: Path | None
    heartbeat_sec: float | None
    no_in_turn_heartbeat: bool
    mode: str
    max_retries_per_turn: int
    retry_backoff_sec: float
    silent_hang_threshold_sec: float


__all__ = ["CompactionParsedArgs"]
