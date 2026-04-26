"""Minimal chat-agent contract runner (CI-friendly, no LLM).

Run: ``python -m eval.chat_agent`` from repo root (or ``.venv/bin/python -m eval.chat_agent``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def _fail(msg: str) -> int:
    print(f"[chat_agent] FAIL: {msg}", file=sys.stderr)
    return 1


def main() -> int:
    from science_graphrag.agent.context.compaction import build_context_compacted_payload
    from science_graphrag.api.agent_v2 import normalize_history_digest_input

    failures: list[str] = []

    p = build_context_compacted_payload(
        thread_id="t",
        session_summary_excerpt="x",
        latest_full_state={"ok": True},
        digest_count=2,
    )
    if p.get("compaction", {}).get("digest_count") != 2:
        failures.append("compaction digest_count")

    rows, inv = normalize_history_digest_input('[{"user":"a"}]')
    if inv or len(rows) != 1:
        failures.append("history_digest normalize")

    for rel in (
        "tests/fixtures/benchmarks/chat_wave_b/multi_turn_memory_smoke_gold.json",
        "tests/fixtures/benchmarks/chat_wave_c/chat_context_compaction_v1_smoke_gold.json",
    ):
        path = _REPO / rel
        if not path.is_file():
            failures.append(f"missing fixture {rel}")
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"invalid json {rel}: {exc}")

    if failures:
        return _fail("; ".join(failures))

    print("[chat_agent] OK: contract checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
