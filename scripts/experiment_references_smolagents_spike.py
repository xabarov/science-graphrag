"""
H2 spike: ToolCallingAgent (smolagents) with whitelist tools over in-memory markdown.

Install optional deps: ``pip install '.[research]'`` (adds smolagents).

Not for production ingestion: research-only benchmark / cost-quality probe.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import typer

app = typer.Typer(add_completion=False, help="H2: smolagents tool-calling spike for references.")


def _run_spike(case_id: str, fixture_root: Path, max_steps: int) -> dict[str, object]:
    from smolagents import OpenAIServerModel, Tool, ToolCallingAgent

    from science_graphrag.config import get_settings
    from science_graphrag.ingestion.stages.references import extract_references

    settings = get_settings()
    api = (settings.benchmark_teacher_llm_api_key or settings.extraction_llm_api_key or "").strip()
    if not api:
        return {"status": "error", "reason": "no_api_key"}

    article_path = fixture_root / case_id / "article.md"
    markdown = article_path.read_text(encoding="utf-8")

    class HeuristicRefsTool(Tool):
        name = "heuristic_references"
        description = (
            "Run the project's extract_references() on the full loaded article markdown. "
            "Returns JSON: count, first 5 raw_reference snippets, dois."
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
        description = (
            "Search the loaded article with a Python regex; returns up to 30 lines "
            "(line number: text)."
        )
        inputs = {
            "pattern": {
                "type": "string",
                "description": "Python re pattern (e.g. References|\\\\[1\\\\])",
            },
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
        description = "Return a 1-based inclusive slice of lines from the loaded article."
        inputs = {
            "start_line": {
                "type": "integer",
                "description": "First line number (1-based)",
            },
            "end_line": {
                "type": "integer",
                "description": "Last line number inclusive",
            },
        }
        output_type = "string"

        def __init__(self, text: str) -> None:
            super().__init__()
            self._text = text

        def forward(self, start_line: int, end_line: int) -> str:
            lines = self._text.splitlines()
            s = max(0, int(start_line) - 1)
            e = min(len(lines), int(end_line))
            chunk = "\n".join(lines[s:e])
            return chunk[:60_000] if chunk else "(empty)"

    model = OpenAIServerModel(
        model_id=settings.extraction_llm_model,
        api_key=api,
        api_base=settings.extraction_llm_base_url,
    )
    tools = [
        HeuristicRefsTool(markdown),
        GrepArticleTool(markdown),
        GetLinesTool(markdown),
    ]
    agent = ToolCallingAgent(
        tools=tools,
        model=model,
        max_steps=max_steps,
        add_base_tools=False,
        instructions=(
            "You only have in-memory article tools. Goal: estimate how many bibliography "
            "references exist. Prefer calling heuristic_references once; use grep_article "
            "or get_lines only if you must verify where the references section starts."
        ),
    )
    task = (
        "How many references does this article's bibliography contain? "
        "Give a single integer final answer after using tools."
    )
    result = agent.run(task)
    return {
        "status": "ok",
        "case_id": case_id,
        "max_steps": max_steps,
        "final_answer": str(result),
        "heuristic_baseline_count": len(extract_references(markdown)),
    }


@app.command()
def main(
    fixture_root: Path = typer.Option(Path("tests/fixtures/benchmarks/layer1")),
    case_id: str = typer.Option("yolov1"),
    max_steps: int = typer.Option(10, ge=1, le=30),
    output_path: Path | None = typer.Option(None),
) -> None:
    try:
        import smolagents  # noqa: F401
    except ImportError:
        payload = {
            "status": "skipped",
            "reason": "smolagents not installed; pip install '.[research]'",
        }
        typer.echo(json.dumps(payload, ensure_ascii=False))
        raise typer.Exit(0)

    payload = _run_spike(case_id, fixture_root, max_steps)
    typer.echo(json.dumps(payload, ensure_ascii=False))
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    app()
