"""
H2 spike: ToolCallingAgent (smolagents) with whitelist tools over in-memory markdown.

Install optional deps: ``pip install '.[research]'`` (adds smolagents).

Not for production ingestion: research-only benchmark / cost-quality probe.

Commands:
  spike  — legacy “count only” task (backward compatible flags).
  suite  — ref_gpt5.4_thoughts variant B (lite): candidates → markers → segment → JSON summary.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer

from eval.references_harness import agent_toolkit as atk
from eval.references_harness.agent_suite_metrics import (
    harness_metrics_for_parsed_span,
    mean_metrics,
)

app = typer.Typer(add_completion=False, help="H2: smolagents tool-calling spike for references.")


def _parse_structured_guess(text: str) -> dict[str, Any]:
    """Best-effort parse of model final answer (JSON block or entry_count field)."""
    raw = text.strip()
    out: dict[str, Any] = {"final_answer_raw": raw[:8000]}
    for pattern in (
        r"```(?:json)?\s*(\{[\s\S]*?\})\s*```",
        r"(\{[\s\S]*\"entry_count\"[\s\S]*\})",
    ):
        m = re.search(pattern, raw, re.DOTALL)
        if m:
            try:
                obj = json.loads(m.group(1))
                if isinstance(obj, dict):
                    out.update(obj)
                    return out
            except json.JSONDecodeError:
                continue
    m2 = re.search(r'"entry_count"\s*:\s*(\d+)', raw)
    if m2:
        out["entry_count"] = int(m2.group(1))
        return out
    m3 = re.search(r"\bentry_count\s*[:=]\s*(\d+)", raw, re.I)
    if m3:
        out["entry_count"] = int(m3.group(1))
        return out
    ints = [int(x) for x in re.findall(r"\b(\d{1,4})\b", raw[-200:])]
    if ints:
        out["entry_count_guess_from_last_integers"] = ints[-1]
    return out


def _tier_case_ids(tier_key: str = "references_benchmark_v1") -> list[str]:
    tier_path = Path("tests/fixtures/benchmarks/layer1/case_tiers.json")
    data = json.loads(tier_path.read_text(encoding="utf-8"))
    return list(data.get(tier_key, []))


def _run_agent(
    case_id: str,
    fixture_root: Path,
    max_steps: int,
    *,
    task_mode: str,
) -> dict[str, object]:
    from smolagents import OpenAIServerModel, Tool, ToolCallingAgent

    from science_graphrag.config import get_settings
    from science_graphrag.ingestion.stages.references import extract_references

    settings = get_settings()
    api = (settings.benchmark_teacher_llm_api_key or settings.extraction_llm_api_key or "").strip()
    if not api:
        return {"status": "error", "reason": "no_api_key"}

    article_path = fixture_root / case_id / "article.md"
    markdown = article_path.read_text(encoding="utf-8")
    lines = markdown.splitlines()

    class HeuristicRefsTool(Tool):
        name = "heuristic_references"
        description = (
            "Run extract_references() on the full article. Returns JSON: count and sample snippets."
        )
        inputs: dict = {}
        output_type = "string"

        def __init__(self, text: str) -> None:
            super().__init__()
            self._text = text

        def forward(self) -> str:
            refs = extract_references(self._text)
            sample = [
                {
                    "raw_reference": (r.raw_reference or "")[:200],
                    "doi": r.doi,
                    "arxiv_id": r.arxiv_id,
                }
                for r in refs[:5]
            ]
            return json.dumps({"count": len(refs), "sample": sample}, ensure_ascii=False)

    class GrepArticleTool(Tool):
        name = "grep_article"
        description = "Python regex search; up to 30 lines (line: text)."
        inputs = {
            "pattern": {"type": "string", "description": "Python re pattern"},
        }
        output_type = "string"

        def __init__(self, text: str) -> None:
            super().__init__()
            self._text = text

        def forward(self, pattern: str) -> str:
            try:
                rx = re.compile(pattern)
            except re.error as e:
                return f"invalid_regex: {e}"
            out: list[str] = []
            for i, line in enumerate(self._text.splitlines(), start=1):
                if rx.search(line):
                    out.append(f"{i}: {line[:500]}")
                if len(out) >= 30:
                    break
            return "\n".join(out) if out else "(no matches)"

    class GetLinesTool(Tool):
        name = "get_lines"
        description = "1-based inclusive line slice from the article."
        inputs = {
            "start_line": {"type": "integer", "description": "First line (1-based)"},
            "end_line": {"type": "integer", "description": "Last line inclusive"},
        }
        output_type = "string"

        def __init__(self, text: str) -> None:
            super().__init__()
            self._text = text

        def forward(self, start_line: int, end_line: int) -> str:
            ls = self._text.splitlines()
            s = max(0, int(start_line) - 1)
            e = min(len(ls), int(end_line))
            chunk = "\n".join(ls[s:e])
            return chunk[:60_000] if chunk else "(empty)"

    class FindBibliographyCandidatesTool(Tool):
        name = "find_bibliography_candidates"
        description = (
            "List heuristic bibliography zones with start_line, end_line, and marker densities "
            "(bracket [n], numeric n., DOI, arXiv, years). Call this first."
        )
        inputs: dict = {}
        output_type = "string"

        def __init__(self, text: str) -> None:
            super().__init__()
            self._text = text

        def forward(self) -> str:
            c = atk.bibliography_candidates(self._text)
            return json.dumps(c, ensure_ascii=False, indent=2)[:50_000]

    class CountReferenceMarkersTool(Tool):
        name = "count_reference_markers"
        description = "Count citation-like markers in a 1-based inclusive line range."
        inputs = {
            "start_line": {
                "type": "integer",
                "description": "First line number (1-based, inclusive)",
            },
            "end_line": {
                "type": "integer",
                "description": "Last line number (1-based, inclusive)",
            },
        }
        output_type = "string"

        def __init__(self, line_list: list[str]) -> None:
            super().__init__()
            self._lines = line_list

        def forward(self, start_line: int, end_line: int) -> str:
            r = atk.count_reference_markers(self._lines, int(start_line), int(end_line))
            return json.dumps(r, ensure_ascii=False)

    class SegmentReferenceBlockTool(Tool):
        name = "segment_reference_block"
        description = (
            "Split bibliography lines into entries (deterministic). Optional style_hint: "
            "auto, bracket_numbered, numeric_dot, author_year."
        )
        inputs = {
            "start_line": {
                "type": "integer",
                "description": "First bibliography line (1-based, inclusive)",
            },
            "end_line": {
                "type": "integer",
                "description": "Last bibliography line (1-based, inclusive)",
            },
            "style_hint": {
                "type": "string",
                "description": "empty or auto | bracket_numbered | numeric_dot | author_year",
                "nullable": True,
            },
        }
        output_type = "string"

        def __init__(self, line_list: list[str]) -> None:
            super().__init__()
            self._lines = line_list

        def forward(self, start_line: int, end_line: int, style_hint: str | None = None) -> str:
            hint = (style_hint or "").strip() or None
            if hint == "auto":
                hint = None
            r = atk.segment_reference_block_lines(
                self._lines, int(start_line), int(end_line), style_hint=hint
            )
            return json.dumps(r, ensure_ascii=False)

    model = OpenAIServerModel(
        model_id=settings.extraction_llm_model,
        api_key=api,
        api_base=settings.extraction_llm_base_url,
    )

    if task_mode == "count":
        tools = [
            HeuristicRefsTool(markdown),
            GrepArticleTool(markdown),
            GetLinesTool(markdown),
        ]
        instructions = (
            "You only have in-memory article tools. Goal: estimate how many bibliography "
            "references exist. Prefer heuristic_references once; use grep_article or get_lines "
            "only if you must verify where the references section starts."
        )
        task = (
            "How many references does this article's bibliography contain? "
            "Give a single integer final answer after using tools."
        )
    else:
        tools = [
            FindBibliographyCandidatesTool(markdown),
            CountReferenceMarkersTool(lines),
            SegmentReferenceBlockTool(lines),
            HeuristicRefsTool(markdown),
            GrepArticleTool(markdown),
            GetLinesTool(markdown),
        ]
        instructions = (
            "You are a bibliography router (ref_gpt5.4_thoughts variant B). "
            "1) Call find_bibliography_candidates. "
            "2) Optionally count_reference_markers on the best range. "
            "3) Call segment_reference_block with start_line, end_line, and style_hint auto "
            "(or bracket_numbered / numeric_dot / author_year if obvious). "
            "4) If needed, cross-check with heuristic_references or get_lines. "
            "Final message MUST be a single JSON object with keys: "
            "start_line (int), end_line (int), entry_count (int), style_guess (string), "
            "confidence (0-1 float), reasoning_summary (short string)."
        )
        task = (
            "Localize the main bibliography block and report how many reference entries it contains. "
            "Use tools; end with the JSON object from your instructions."
        )

    agent = ToolCallingAgent(
        tools=tools,
        model=model,
        max_steps=max_steps,
        add_base_tools=False,
        instructions=instructions,
    )
    t0 = time.perf_counter()
    result = agent.run(task)
    wall = round(time.perf_counter() - t0, 3)
    base: dict[str, object] = {
        "status": "ok",
        "case_id": case_id,
        "task_mode": task_mode,
        "max_steps": max_steps,
        "final_answer": str(result),
        "wall_seconds": wall,
        "heuristic_baseline_count": len(extract_references(markdown)),
    }
    if task_mode == "router":
        parsed = _parse_structured_guess(str(result))
        base["parsed"] = parsed
        ec = parsed.get("entry_count")
        if ec is None:
            ec = parsed.get("entry_count_guess_from_last_integers")
        base["parsed_entry_count"] = ec
    return base


@app.command("spike")
def cmd_spike(
    fixture_root: Path = typer.Option(Path("tests/fixtures/benchmarks/layer1")),
    case_id: str = typer.Option("yolov1"),
    max_steps: int = typer.Option(10, help="Max agent steps (1–30)."),
    output_path: Path | None = typer.Option(None),
) -> None:
    """Legacy task: estimate reference count (integer answer)."""
    try:
        import smolagents  # noqa: F401
    except ImportError:
        typer.echo(
            json.dumps(
                {
                    "status": "skipped",
                    "reason": "smolagents not installed; pip install '.[research]'",
                },
                ensure_ascii=False,
            )
        )
        raise typer.Exit(0)

    max_steps = max(1, min(30, max_steps))
    payload = _run_agent(case_id, fixture_root, max_steps, task_mode="count")
    typer.echo(json.dumps(payload, ensure_ascii=False))
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )


@app.command("suite")
def cmd_suite(
    fixture_root: Path = typer.Option(Path("tests/fixtures/benchmarks/layer1")),
    output_path: Path | None = typer.Option(
        None,
        help="Defaults to eval/results/refs_agent_suite_<utc_timestamp>.json",
    ),
    max_steps: int = typer.Option(14, help="Max agent steps per case (1–30)."),
    tier: str = typer.Option(
        "references_benchmark_v1",
        "--tier",
        help="Key in case_tiers.json (e.g. references_benchmark_v1, references_benchmark_full).",
    ),
    case_arg: list[str] = typer.Option(
        [],
        "--case",
        help="Restrict to these case ids; default: cases from --tier.",
    ),
) -> None:
    """
    Run router on tier cases; LLM dialog plus harness-aligned metrics (span IoU, entry F1).

    Writes JSON with ``per_mode_mean.agent_router`` compatible with ``refs_bench_summary`` shape.
    """
    try:
        import smolagents  # noqa: F401
    except ImportError:
        typer.echo(
            json.dumps(
                {
                    "status": "skipped",
                    "reason": "smolagents not installed; pip install '.[research]'",
                },
                ensure_ascii=False,
            )
        )
        raise typer.Exit(0)

    max_steps = max(1, min(30, max_steps))
    case_ids = case_arg if case_arg else _tier_case_ids(tier)
    if not case_ids:
        raise typer.BadParameter("No cases")

    from eval.layer1.spec import Layer1GoldSpec

    out_path = output_path
    if out_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = Path(f"eval/results/refs_agent_suite_{ts}.json")

    t_cli = time.perf_counter()
    rows: list[dict[str, object]] = []
    errors = 0
    for cid in case_ids:
        gold_path = fixture_root / cid / "gold.json"
        gold_n: int | None = None
        rb = None
        if gold_path.is_file():
            spec = Layer1GoldSpec.load(gold_path)
            rb = spec.references_benchmark
            if rb is not None:
                gold_n = len(rb.raw_entries)
        row = _run_agent(cid, fixture_root, max_steps, task_mode="router")
        if row.get("status") != "ok":
            errors += 1
        row["mode"] = "agent_router"
        article_path = fixture_root / cid / "article.md"
        if rb is not None and article_path.is_file():
            lines = article_path.read_text(encoding="utf-8").splitlines()
            parsed = row.get("parsed")
            parsed_dict = parsed if isinstance(parsed, dict) else {}
            hm = harness_metrics_for_parsed_span(
                lines,
                rb.bibliography.start_line,
                rb.bibliography.end_line,
                rb.raw_entries,
                parsed_dict,
            )
            row.update(hm)
            row["abs_error_vs_gold"] = hm.get("count_abs_error")
        else:
            row["metrics_note"] = "skipped_harness_metrics_no_gold_or_article"
            pred = row.get("parsed_entry_count")
            abs_err = None
            if gold_n is not None and pred is not None:
                abs_err = abs(int(pred) - gold_n)
            row["gold_entry_count"] = gold_n
            row["abs_error_vs_gold"] = abs_err

        if row.get("gold_entry_count") is None and gold_n is not None:
            row["gold_entry_count"] = gold_n
        pred = row.get("parsed_entry_count")
        if row.get("abs_error_vs_gold") is None and gold_n is not None and pred is not None:
            row["abs_error_vs_gold"] = abs(int(pred) - gold_n)

        rows.append(row)

    cli_s = round(time.perf_counter() - t_cli, 3)
    summary = {
        "schema": "refs_agent_suite_v2",
        "compatible_summary_keys": "per_mode_mean matches refs_bench_summary.json",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "fixture_root": str(fixture_root),
        "case_ids": case_ids,
        "max_steps": max_steps,
        "errors": errors,
        "cli_wall_seconds": cli_s,
        "rows": rows,
        "per_mode_mean": {"agent_router": mean_metrics([dict(r) for r in rows])},
    }
    abs_errors = [r["abs_error_vs_gold"] for r in rows if r.get("abs_error_vs_gold") is not None]
    if abs_errors:
        summary["mean_abs_error_vs_gold"] = sum(abs_errors) / len(abs_errors)
        summary["median_abs_error_vs_gold"] = sorted(abs_errors)[len(abs_errors) // 2]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    pm = summary["per_mode_mean"]["agent_router"]
    typer.echo(
        json.dumps(
            {
                "status": "ok",
                "wrote": str(out_path),
                "n_cases": len(case_ids),
                "errors": errors,
                "cli_wall_seconds": cli_s,
                "mean_span_line_iou": pm.get("mean_span_line_iou"),
                "mean_entry_overlap_f1": pm.get("mean_entry_overlap_f1"),
                "mean_abs_error_vs_gold": summary.get("mean_abs_error_vs_gold"),
                "median_abs_error_vs_gold": summary.get("median_abs_error_vs_gold"),
            },
            ensure_ascii=False,
        )
    )
    typer.echo(f"Wrote {out_path}")


def main() -> None:
    app()


if __name__ == "__main__":
    import sys

    _sub = ("spike", "suite")
    if len(sys.argv) >= 2 and sys.argv[1] in _sub:
        main()
    else:
        sys.argv.insert(1, "spike")
        main()
