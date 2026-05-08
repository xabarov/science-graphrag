"""Pairwise LLM judge (or deterministic heuristic fallback) for v3 quality benchmark."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from eval.agent_v3_quality.contract import RUBRIC_AXES
from eval.agent_v3_quality.judge_metrics import weighted_score_from_axes
from science_graphrag.agent.llm.chat import build_chat_model, effective_chat_llm_model
from science_graphrag.config import get_settings

JUDGE_PROMPT_PATH = Path(__file__).with_name("judge_prompt_v1.md")

HARD_FAIL_KEYS = (
    "final_answer_missing",
    "ungrounded_major_claim",
    "ignored_requested_compare",
    "ignored_requested_quote_or_evidence",
    "self_contradiction",
    "non_answer",
)


def judge_prompt_fingerprint() -> str:
    """Short sha256 prefix of ``judge_prompt_v1.md`` for artifact metadata."""

    return "sha256-20:" + hashlib.sha256(JUDGE_PROMPT_PATH.read_bytes()).hexdigest()[:20]


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Parse first JSON object from model output (strip fences, scan braces)."""

    raw = text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    for opener, ch0 in enumerate(raw):
        if ch0 != "{":
            continue
        depth = 0
        for i in range(opener, len(raw)):
            ch = raw[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(raw[opener : i + 1])
                        return obj if isinstance(obj, dict) else None
                    except json.JSONDecodeError:
                        break
    return None


def _heuristic_hard_fails(answer: str) -> list[str]:
    ans = (answer or "").strip()
    if not ans:
        return ["final_answer_missing"]
    return []


def _heuristic_pairwise_judge(
    *,
    _question: str,
    _gold: dict[str, Any],
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic judge for CI / missing API key."""

    b_ans = str(baseline.get("answer") or "").strip()
    c_ans = str(candidate.get("answer") or "").strip()
    b_fails = _heuristic_hard_fails(b_ans)
    c_fails = _heuristic_hard_fails(c_ans)

    def base_scores(answer: str, fails: list[str]) -> dict[str, int]:
        if fails:
            return {k: 2 for k in RUBRIC_AXES}
        score = 4 if len(answer) > 80 else 3
        return {k: score for k in RUBRIC_AXES}

    b_scores = base_scores(b_ans, b_fails)
    c_scores = base_scores(c_ans, c_fails)
    # Light preference for longer grounded-looking answers when both non-empty.
    if c_ans and (not b_ans or len(c_ans) > len(b_ans) + 50):
        winner = "candidate"
    elif b_ans and (not c_ans or len(b_ans) > len(c_ans) + 50):
        winner = "baseline"
    elif len(c_fails) < len(b_fails):
        winner = "candidate"
    elif len(b_fails) < len(c_fails):
        winner = "baseline"
    else:
        winner = "tie"
    return {
        "baseline": {"scores": b_scores, "hard_fail_flags": b_fails},
        "candidate": {"scores": c_scores, "hard_fail_flags": c_fails},
        "pairwise": {
            "winner": winner,
            "confidence": "low",
            "rationale": (
                "heuristic_judge_no_llm: compare answer length, "
                "hard-fail heuristics, and gold requirements"
            ),
        },
    }


def _run_llm_pairwise(  # pylint: disable=too-many-locals
    *,
    question: str,
    gold: dict[str, Any],
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    settings = get_settings()
    llm = build_chat_model(settings, temperature=0.05, max_tokens=900)
    system = JUDGE_PROMPT_PATH.read_text(encoding="utf-8").strip()
    meta = json.dumps(
        {
            "family": gold.get("family"),
            "tags": gold.get("tags"),
            "requires_quotes": gold.get("requires_quotes"),
            "requires_compare_structure": gold.get("requires_compare_structure"),
            "requires_relation_reasoning": gold.get("requires_relation_reasoning"),
        },
        ensure_ascii=False,
    )
    b_ans = str(baseline.get("answer") or "")[:8000]
    c_ans = str(candidate.get("answer") or "")[:8000]
    b_cites = json.dumps(baseline.get("citations") or [], ensure_ascii=False)[:6000]
    c_cites = json.dumps(candidate.get("citations") or [], ensure_ascii=False)[:6000]
    b_trace = str(baseline.get("tool_trace_summary") or "")[:4000]
    c_trace = str(candidate.get("tool_trace_summary") or "")[:4000]
    br = baseline.get("agent_runtime_label")
    cr = candidate.get("agent_runtime_label")
    human = (
        f"USER_QUESTION:\n{question}\n\n"
        f"CASE_METADATA:\n{meta}\n\n"
        f"BASELINE (runtime={br}):\nANSWER:\n{b_ans}\n\n"
        f"CITATIONS_JSON:\n{b_cites}\n\nTOOL_TRACE_SUMMARY:\n{b_trace}\n\n"
        f"CANDIDATE (runtime={cr}):\nANSWER:\n{c_ans}\n\n"
        f"CITATIONS_JSON:\n{c_cites}\n\nTOOL_TRACE_SUMMARY:\n{c_trace}\n"
    )
    msg = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    parsed = _extract_json_object(str(getattr(msg, "content", "") or ""))
    if not parsed:
        return _heuristic_pairwise_judge(
            _question=question, _gold=gold, baseline=baseline, candidate=candidate
        )
    return parsed


def _normalize_branch(parsed: dict[str, Any], side: str) -> dict[str, Any]:
    """Normalize baseline/candidate judge block including scores and flags."""

    block = parsed.get(side) if isinstance(parsed.get(side), dict) else {}
    scores_raw = block.get("scores") if isinstance(block.get("scores"), dict) else {}
    scores: dict[str, int] = {}
    for axis in RUBRIC_AXES:
        try:
            v = int(scores_raw.get(axis, 0))
        except (TypeError, ValueError):
            v = 0
        scores[axis] = max(0, min(6, v))
    flags_raw = block.get("hard_fail_flags")
    flags = [str(x) for x in flags_raw] if isinstance(flags_raw, list) else []
    flags = [f for f in flags if f in HARD_FAIL_KEYS or f in ("parse_failed",)]
    w = weighted_score_from_axes(scores)
    return {
        "scores": scores,
        "hard_fail_flags": flags,
        "weighted_score": round(w, 4) if w is not None else None,
    }


def run_pairwise_judge_for_case(
    *,
    question: str,
    gold: dict[str, Any],
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    use_llm: bool,
) -> dict[str, Any]:
    """Return merged baseline/candidate blocks plus pairwise verdict and ``passed``."""

    if use_llm and not str(get_settings().extraction_llm_api_key or "").strip():
        use_llm = False
    if use_llm:
        raw = _run_llm_pairwise(
            question=question, gold=gold, baseline=baseline, candidate=candidate
        )
    else:
        raw = _heuristic_pairwise_judge(
            _question=question, _gold=gold, baseline=baseline, candidate=candidate
        )

    b_norm = _normalize_branch(raw, "baseline")
    c_norm = _normalize_branch(raw, "candidate")
    pw_raw = raw.get("pairwise") if isinstance(raw.get("pairwise"), dict) else {}
    winner = str(pw_raw.get("winner") or "tie").strip().lower()
    if winner not in {"baseline", "candidate", "tie"}:
        winner = "tie"
    confidence = str(pw_raw.get("confidence") or "low").strip().lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"
    rationale = str(pw_raw.get("rationale") or "")[:800]

    b_set = set(b_norm["hard_fail_flags"])
    c_set = set(c_norm["hard_fail_flags"])
    passed = not b_set and not c_set

    return {
        "baseline": {**baseline, **b_norm},
        "candidate": {**candidate, **c_norm},
        "pairwise": {"winner": winner, "confidence": confidence, "rationale": rationale},
        "passed": passed,
    }


def judge_meta(*, llm: bool) -> dict[str, Any]:
    """Metadata fields embedded in suite ``run_metadata``."""

    settings = get_settings()
    return {
        "judge_prompt_version": "judge_prompt_v1",
        "judge_prompt_sha256": judge_prompt_fingerprint(),
        "judge_llm_model": effective_chat_llm_model(settings) if llm else None,
        "llm_rubric": bool(llm),
    }
