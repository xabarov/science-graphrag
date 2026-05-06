"""Advisory judge for Wave R agent tool-use benchmarks."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import typer
from langchain_core.messages import HumanMessage, SystemMessage

from eval.bench_common import benchmark_run_metadata
from science_graphrag.agent.llm.chat import build_chat_model, effective_chat_llm_model
from science_graphrag.config import get_settings

JUDGE_PROMPT_PATH = Path(__file__).with_name("judge_prompt_v1.md")
JUDGE_LLM_PROMPT_PATH = Path(__file__).with_name("judge_prompt_llm_v1.md")


def judge_prompt_fingerprint() -> str:
    return "sha256-20:" + hashlib.sha256(JUDGE_PROMPT_PATH.read_bytes()).hexdigest()[:20]


def judge_llm_prompt_fingerprint() -> str:
    return "sha256-20:" + hashlib.sha256(JUDGE_LLM_PROMPT_PATH.read_bytes()).hexdigest()[:20]


def _default_fixtures_root() -> Path:
    return Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "benchmarks" / "agent_tools_v1"


def _resolve_question(case_row: dict[str, Any], fixtures_root: Path) -> str:
    q = str(case_row.get("question") or "").strip()
    if q:
        return q
    cid = str(case_row.get("case_id") or "").strip()
    if not cid:
        return ""
    p = fixtures_root / cid / "question.txt"
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return ""


def _extract_json_object(text: str) -> dict[str, Any] | None:
    raw = text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    for opener in range(len(raw)):
        if raw[opener] != "{":
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


def _run_llm_case_score(
    *,
    settings: Any,
    question: str,
    case_row: dict[str, Any],
) -> tuple[float, str, list[str]]:
    """Return (weighted_score 0..6, rationale, flags)."""

    llm = build_chat_model(settings, temperature=0.05, max_tokens=512)
    system = JUDGE_LLM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    trace_blob = json.dumps(case_row.get("tool_trace") or [], ensure_ascii=False, default=str)[
        :12000
    ]
    cites_blob = json.dumps(case_row.get("citations") or [], ensure_ascii=False)[:4000]
    human = (
        f"USER_QUESTION:\n{question}\n\n"
        f"ANSWER:\n{str(case_row.get('answer') or '')[:8000]}\n\n"
        f"CITATIONS_JSON:\n{cites_blob}\n\n"
        f"TOOL_TRACE_JSON:\n{trace_blob}\n"
    )
    msg = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    parsed = _extract_json_object(str(getattr(msg, "content", "") or ""))
    if not parsed:
        return 0.0, "judge_parse_failed", ["parse_failed"]
    try:
        score_i = int(parsed.get("score"))
    except (TypeError, ValueError):
        return 0.0, "judge_missing_score", ["missing_score"]
    score_i = max(0, min(6, score_i))
    rationale = str(parsed.get("rationale") or "").strip() or "no_rationale"
    flags_raw = parsed.get("flags")
    flags = [str(x) for x in flags_raw] if isinstance(flags_raw, list) else []
    return float(score_i), rationale, flags


def run_agent_judge(path: Path, *, llm: bool = False, fixtures_root: Path | None = None) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("cases") or []
    settings = get_settings()
    fx = fixtures_root or _default_fixtures_root()
    judged: list[dict[str, Any]] = []

    if llm and not str(settings.extraction_llm_api_key or "").strip():
        raise RuntimeError(
            "LLM judge requires SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY (or host .env). "
            "Use heuristic mode without --llm for offline CI.",
        )

    for row in rows:
        if not isinstance(row, dict):
            continue
        cid = row.get("case_id")
        err = row.get("error")
        if err:
            judged.append(
                {
                    "case_id": cid,
                    "weighted_score": 0.0,
                    "passed": False,
                    "rationale": f"benchmark_error: {err}",
                    "flags": ["benchmark_error"],
                },
            )
            continue

        if llm:
            question = _resolve_question(row, fx)
            score_f, rationale, flags = _run_llm_case_score(
                settings=settings,
                question=question,
                case_row=row,
            )
            judged.append(
                {
                    "case_id": cid,
                    "weighted_score": score_f,
                    "passed": bool(score_f >= 4.0),
                    "rationale": rationale,
                    "flags": flags,
                },
            )
        else:
            score = 4.0
            if (row.get("metrics") or {}).get("tool_call_correctness", 0.0) >= 0.8:
                score = 4.8
            judged.append({"case_id": cid, "weighted_score": score, "passed": score >= 4.0})

    mean = sum(float(r["weighted_score"]) for r in judged) / len(judged) if judged else None
    schema = "agent_tools_judge_v2_llm" if llm else "agent_tools_judge_v1"
    fp = judge_llm_prompt_fingerprint() if llm else judge_prompt_fingerprint()
    meta = {
        **benchmark_run_metadata(settings),
        "judge_prompt_fingerprint": fp,
        "judge_schema_version": schema,
        "agent_tools_artifact": str(path),
        "judge_llm_model": effective_chat_llm_model(settings) if llm else None,
    }
    return {
        "run_metadata": meta,
        "summary": {
            "case_count": len(judged),
            "mean_weighted_score": mean,
            "all_passed": all(bool(x.get("passed")) for x in judged) if judged else True,
            "agent_tools_judge_eval": True,
            "llm_rubric": bool(llm),
        },
        "cases": judged,
    }


def _cli(
    agent_tools_json: Path = typer.Argument(..., exists=True, readable=True),
    json_out: Path | None = typer.Option(None, "--json-out"),
    llm: bool = typer.Option(
        False,
        "--llm/--no-llm",
        help="Score each case with the chat LLM rubric (needs extraction LLM API key).",
    ),
    fixtures_root: Path | None = typer.Option(
        None,
        "--fixtures-root",
        exists=True,
        file_okay=False,
        help="Root containing <case_id>/question.txt when missing from artifact JSON.",
    ),
) -> None:
    try:
        payload = run_agent_judge(agent_tools_json, llm=llm, fixtures_root=fixtures_root)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    txt = json.dumps(payload, indent=2, ensure_ascii=False)
    typer.echo(txt)
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(txt + "\n", encoding="utf-8")


def main() -> None:
    typer.run(_cli)


if __name__ == "__main__":
    main()
