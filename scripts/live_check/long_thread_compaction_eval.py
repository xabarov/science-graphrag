#!/usr/bin/env python3
"""Wave H §H1 long-thread compaction harness (deterministic, offline).

Drives a 50-turn workspace conversation through the in-memory session backend,
exercising:

* L4 LLM compact boundary (``maybe_llm_compact_session_after_turn``) with a stub
  side-LLM that emits a stable summary plus realistic cache telemetry.
* Per-turn post-compact hook chain (``run_post_compact_hooks``) so paper-source
  carry-over is observable.
* ``format_user_with_memory`` rendering on the next turn so we can assert that
  paper sources actually appear in the prompt rather than just in session_meta.

Outputs are paired baseline vs candidate-friendly artifacts:

* ``--out-json`` — structured turn-by-turn record + aggregate metrics shaped to
  flow through ``trace_review_schema.aggregate_metrics_from_timeline`` semantics
  (subset relevant to compaction).
* ``--out-md``  — human-readable markdown summary used by SOP runbook.

The harness is intentionally **offline**: it does not contact any LLM provider,
so it is safe to run on every CI build and produces stable artifacts for
``trace_regression_compare.py``. Live-LLM acceptance for compaction will reuse
the trace-review pipeline via ``compaction_turn_review.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from langchain_core.messages import ToolMessage  # noqa: E402

import science_graphrag.agent.context.llm_history_compact as llm_history_compact_mod  # noqa: E402
from science_graphrag.agent.context.llm_history_compact import (  # noqa: E402
    L4SummaryResult,
    maybe_llm_compact_session_after_turn,
)
from science_graphrag.agent.context.post_compact_attachments import (  # noqa: E402
    clear_paper_sources_capsule,
    load_paper_sources_items,
)
from science_graphrag.agent.context.session_backend import (  # noqa: E402
    InMemorySessionMemoryBackend,
    get_session_memory_backend,
    set_session_memory_backend,
)
from science_graphrag.agent.context.session_store import (  # noqa: E402
    format_user_with_memory,
    get_session_for_thread,
    update_session_after_turn,
)
from science_graphrag.agent.forked_runtime import SideLlmRunResult  # noqa: E402
from science_graphrag.agent.hooks import run_post_compact_hooks  # noqa: E402
from science_graphrag.config import Settings  # noqa: E402


@dataclass(frozen=True, slots=True)
class TurnRecord:
    """One synthetic compaction-loop turn snapshot for per-turn artefact rows."""

    turn: int
    digest_count_before: int
    compact_triggered: bool
    paper_sources_saved: int
    paper_sources_restored: int
    side_llm_cache_read_ratio: float | None
    forked: bool
    ptl_retry_count: int


# Two well-known "papers" the synthetic agent supposedly grounds on. Stable IDs
# allow the trace-review compare script to detect drift across runs.
_PAPER_W1 = {"work_id": "w-bert", "snippet": "Pre-training of deep bidirectional transformers"}
_PAPER_W2 = {"work_id": "w-roberta", "snippet": "A robustly optimized BERT pretraining approach"}


def _stub_summary_result(profile: str, turn: int) -> L4SummaryResult:
    """Build a stable side-LLM completion with realistic cache telemetry.

    Two profiles are exposed so a paired run can simulate Wave H §H2 cache benefit:

    * ``baseline`` — pre-Wave-H telemetry shape (``cache_read=0`` everywhere; ratio
      is 0.0 once cache fields are reported), modelling the previous L4 path that
      never went through ``run_side_llm_chat`` and thus never benefitted from
      shared-prefix caching.
    * ``candidate`` — Wave H §H2 path with stable system prompt; cache hit ratio
      grows with turn index as more compaction calls share the same prefix.
    """
    if profile == "baseline":
        return L4SummaryResult(
            text=f"summary_v1 turn={turn}",
            fork=SideLlmRunResult(
                text=f"summary_v1 turn={turn}",
                forked=True,
                latency_ms=120,
                side_llm_cache_read_tokens=0,
                side_llm_cache_creation_tokens=900,
                side_llm_cache_read_ratio=0.0,
            ),
        )
    cache_read = 600 + min(turn, 30) * 20
    cache_creation = 200
    denom = float(cache_read + cache_creation)
    ratio = round(cache_read / denom, 4) if denom > 0 else 0.0
    return L4SummaryResult(
        text=f"summary_v1 turn={turn}",
        fork=SideLlmRunResult(
            text=f"summary_v1 turn={turn}",
            forked=True,
            latency_ms=80,
            side_llm_cache_read_tokens=cache_read,
            side_llm_cache_creation_tokens=cache_creation,
            side_llm_cache_read_ratio=ratio,
        ),
    )


def _paper_messages_for_turn(turn: int) -> list[ToolMessage]:
    """Two ToolMessages mirroring an idea_search + paper_quote_search hop."""
    return [
        ToolMessage(
            content=json.dumps({"items": [_PAPER_W1, _PAPER_W2]}),
            tool_call_id=f"tc-idea-{turn}",
            name="idea_search",
        ),
        ToolMessage(
            content=json.dumps(
                {
                    "quote_candidates": [
                        {
                            "work_id": _PAPER_W1["work_id"],
                            "quote_text": "We introduce a new language representation model.",
                        }
                    ]
                }
            ),
            tool_call_id=f"tc-quote-{turn}",
            name="paper_quote_search",
        ),
    ]


def _build_settings(*, digest_cap: int) -> Settings:
    return Settings.model_construct(
        agent_llm_full_history_compact_enabled=True,
        agent_llm_full_history_compact_cooldown_turns=1,
        agent_compaction_digest_cap=digest_cap,
        extraction_llm_api_key="sk-test-key",
        extraction_llm_base_url="https://example.invalid/v1",
        extraction_llm_model="unused-for-test",
        extraction_llm_timeout_seconds=30,
        chat_llm_model="",
        agent_llm_full_history_compact_max_out_tokens=512,
        agent_llm_full_history_compact_max_digest_chars=8000,
        agent_post_compact_paper_sources_enabled=True,
        agent_post_compact_paper_sources_max_items=12,
        agent_pre_compact_sanitizers_enabled=True,
    )


def _drive_thread(  # pylint: disable=too-many-locals
    *,
    profile: str,
    turns: int,
    digest_cap: int,
    monkeypatched_summary,
) -> tuple[list[TurnRecord], str]:
    """Run the synthetic 50-turn loop; return per-turn records + thread id."""
    tid = f"wave_h_long_{profile}_{uuid.uuid4().hex[:8]}"
    settings = _build_settings(digest_cap=digest_cap)

    records: list[TurnRecord] = []
    for turn in range(1, turns + 1):
        update_session_after_turn(
            tid,
            turn_digest={
                "user_intent": f"turn-{turn}: ask about masked LM",
                "answer_excerpt": (
                    f"turn-{turn}: BERT (work_id=w-bert) introduced masked LM; "
                    f"RoBERTa (work_id=w-roberta) tuned hyperparams."
                ),
                "answer_class": "grounded_explanation",
                "tools_used": ["idea_search", "paper_quote_search"],
            },
        )

        digests_before = len(get_session_for_thread(tid).get("digests") or [])
        # Stub side-LLM call so the harness stays offline.
        monkeypatched_summary["fn"] = lambda settings, user_blob, _turn=turn: _stub_summary_result(
            profile, _turn
        )

        audit = maybe_llm_compact_session_after_turn(
            settings,
            tid,
            digest_count=digests_before,
            digest_cap=digest_cap,
        )

        compact_fired = audit is not None
        side_ratio: float | None = None
        forked = False
        ptl_retries = 0
        if compact_fired and isinstance(audit, dict):
            side_ratio = audit.get("side_llm_cache_read_ratio")
            forked = bool(audit.get("forked"))
            ptl_retries = int(audit.get("ptl_retry_count") or 0)

        # Always exercise the post-compact hook chain after a real compact, mirroring
        # what runtime would do; outside compact boundaries this would no-op.
        paper_saved = 0
        paper_restored = 0
        if compact_fired:
            decisions = run_post_compact_hooks(
                thread_id=tid,
                messages=_paper_messages_for_turn(turn),
                settings=settings,
            )
            persist = next(
                (d for d in decisions if d.hook_id == "post_compact.persist_paper_sources"),
                None,
            )
            if persist is not None:
                paper_saved = int(persist.detail.get("post_compact_paper_sources_saved") or 0)

            # Simulate the next-turn prompt build that would consume the capsule.
            ent = get_session_for_thread(tid)
            loaded = load_paper_sources_items(ent)
            paper_restored = len(loaded)
            prompt = format_user_with_memory(
                question=f"turn-{turn + 1}: follow-up question",
                session_summary=str(ent.get("session_summary") or ""),
                history_digest=[],
                paper_sources_items=loaded,
            )
            if loaded:
                if "<paper_sources_restored>" not in prompt:
                    raise RuntimeError(
                        f"long-thread harness invariant broken at turn {turn}: paper sources "
                        f"loaded ({paper_restored}) but block missing from prompt"
                    )
                clear_paper_sources_capsule(tid)

        records.append(
            TurnRecord(
                turn=turn,
                digest_count_before=digests_before,
                compact_triggered=compact_fired,
                paper_sources_saved=paper_saved,
                paper_sources_restored=paper_restored,
                side_llm_cache_read_ratio=side_ratio,
                forked=forked,
                ptl_retry_count=ptl_retries,
            )
        )

    return records, tid


def _aggregate(records: list[TurnRecord]) -> dict[str, Any]:
    compact_hits = [r for r in records if r.compact_triggered]
    ratios = [
        float(r.side_llm_cache_read_ratio)
        for r in compact_hits
        if r.side_llm_cache_read_ratio is not None
    ]
    paper_total = sum(r.paper_sources_restored for r in compact_hits)
    paper_cases = sum(1 for r in compact_hits if r.paper_sources_restored > 0)
    return {
        "turns_total": len(records),
        "compaction_event_count": len(compact_hits),
        "side_llm_cache_read_ratio_avg": (round(sum(ratios) / len(ratios), 4) if ratios else None),
        "side_llm_cache_read_ratio_min": round(min(ratios), 4) if ratios else None,
        "side_llm_cache_read_ratio_max": round(max(ratios), 4) if ratios else None,
        "post_compact_paper_sources_restored_total": paper_total,
        "post_compact_paper_sources_restored_cases": paper_cases,
        "ptl_retry_total": sum(r.ptl_retry_count for r in compact_hits),
        "forked_compactions": sum(1 for r in compact_hits if r.forked),
    }


def _verdict(metrics: dict[str, Any], *, min_ratio: float) -> dict[str, Any]:
    fail_reasons: list[str] = []
    warn_reasons: list[str] = []
    if int(metrics["compaction_event_count"]) <= 0:
        fail_reasons.append("no_compaction_events_in_long_thread")
    if int(metrics["post_compact_paper_sources_restored_cases"]) <= 0:
        warn_reasons.append("no_paper_sources_restored_after_any_compaction")
    side_avg = metrics.get("side_llm_cache_read_ratio_avg")
    if side_avg is None:
        warn_reasons.append("side_llm_cache_read_ratio_avg_missing")
    elif float(side_avg) < float(min_ratio):
        warn_reasons.append(
            f"side_llm_cache_read_ratio_avg:{float(side_avg):.4f}<{float(min_ratio):.4f}"
        )
    status = "pass"
    if fail_reasons:
        status = "fail"
    elif warn_reasons:
        status = "warn"
    return {
        "status": status,
        "fail_reasons": fail_reasons,
        "warn_reasons": warn_reasons,
    }


def _write_md(
    path: Path, *, profile: str, metrics: dict[str, Any], verdict: dict[str, Any]
) -> None:
    lines = [
        "# Wave H Long-thread Compaction Eval",
        "",
        f"- Profile: `{profile}`",
        f"- Turns: `{metrics['turns_total']}`",
        f"- Compaction events: `{metrics['compaction_event_count']}`",
        ("- side_llm_cache_read_ratio_avg: " f"`{metrics['side_llm_cache_read_ratio_avg']}`"),
        (
            "- side_llm_cache_read_ratio min/max: "
            f"`{metrics['side_llm_cache_read_ratio_min']}` / "
            f"`{metrics['side_llm_cache_read_ratio_max']}`"
        ),
        (
            "- post_compact_paper_sources_restored cases/total: "
            f"`{metrics['post_compact_paper_sources_restored_cases']}` / "
            f"`{metrics['post_compact_paper_sources_restored_total']}`"
        ),
        f"- forked compactions: `{metrics['forked_compactions']}`",
        f"- ptl retry total: `{metrics['ptl_retry_total']}`",
        "",
        f"## Verdict: `{verdict['status']}`",
    ]
    if verdict["fail_reasons"]:
        lines.append("")
        lines.append("### Fail reasons")
        lines.extend(f"- {r}" for r in verdict["fail_reasons"])
    if verdict["warn_reasons"]:
        lines.append("")
        lines.append("### Warn reasons")
        lines.extend(f"- {r}" for r in verdict["warn_reasons"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--turns", type=int, default=50)
    parser.add_argument("--digest-cap", type=int, default=10)
    parser.add_argument(
        "--profile",
        choices=("baseline", "candidate"),
        default="candidate",
        help=(
            "``baseline`` simulates the pre-Wave-H L4 path (no shared cache prefix). "
            "``candidate`` simulates the Wave H §H2 cache-safe path."
        ),
    )
    parser.add_argument(
        "--min-side-llm-cache-read-ratio",
        type=float,
        default=0.4,
        help="Wave E2 threshold; warn when avg ratio dips below this on candidate runs.",
    )
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args(argv)

    # Safety: always run this harness against an isolated in-memory backend.
    # Never touch a process-configured Redis session store from an offline eval script.
    previous_backend = get_session_memory_backend()
    set_session_memory_backend(InMemorySessionMemoryBackend())
    monkeypatched: dict[str, Any] = {"fn": None}
    # ``_invoke_summary_llm`` is module-private but we deliberately stub it so the
    # harness stays offline; this is the same seam used by ``test_llm_history_compact``.
    real = getattr(llm_history_compact_mod, "_invoke_summary_llm")

    def patched(settings, user_blob):
        """Runtime ``_invoke_summary_llm`` stub used only inside this harness."""
        cb = monkeypatched["fn"]
        if cb is None:
            return real(settings, user_blob=user_blob)
        if not callable(cb):
            raise TypeError("monkeypatched['fn'] must be callable or None")
        return cb(settings, user_blob)

    setattr(llm_history_compact_mod, "_invoke_summary_llm", patched)
    try:
        records, tid = _drive_thread(
            profile=args.profile,
            turns=int(args.turns),
            digest_cap=int(args.digest_cap),
            monkeypatched_summary=monkeypatched,
        )
    finally:
        setattr(llm_history_compact_mod, "_invoke_summary_llm", real)
        try:
            get_session_memory_backend().clear_all()
        finally:
            set_session_memory_backend(previous_backend)

    metrics = _aggregate(records)
    verdict = _verdict(metrics, min_ratio=float(args.min_side_llm_cache_read_ratio))
    payload = {
        "schema_version": "wave_h_long_thread_eval_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "profile": args.profile,
        "thread_id": tid,
        "params": {
            "turns": int(args.turns),
            "digest_cap": int(args.digest_cap),
            "min_side_llm_cache_read_ratio": float(args.min_side_llm_cache_read_ratio),
        },
        "metrics": metrics,
        "verdict": verdict,
        "turns": [
            {
                "turn": r.turn,
                "digest_count_before": r.digest_count_before,
                "compact_triggered": r.compact_triggered,
                "paper_sources_saved": r.paper_sources_saved,
                "paper_sources_restored": r.paper_sources_restored,
                "side_llm_cache_read_ratio": r.side_llm_cache_read_ratio,
                "forked": r.forked,
                "ptl_retry_count": r.ptl_retry_count,
            }
            for r in records
        ],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_md(args.out_md, profile=args.profile, metrics=metrics, verdict=verdict)
    print(f"[wave-h-long-thread] json: {args.out_json}")
    print(f"[wave-h-long-thread] md:   {args.out_md}")
    print(f"[wave-h-long-thread] verdict: {verdict['status']}")
    if verdict["status"] == "fail":
        return 1
    if verdict["status"] == "warn":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
