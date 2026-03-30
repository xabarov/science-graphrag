from __future__ import annotations

from pathlib import Path

import typer

from science_graphrag.ingestion.pipeline import run_ingest_cli

app = typer.Typer(no_args_is_help=True, help="science-graphrag CLI")


@app.callback()
def _root() -> None:
    """Scholarly GraphRAG — ingestion and graph backbone."""


@app.command("ingest")
def ingest_cmd(
    path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="PDF or .txt file",
    ),
) -> None:
    """Run Phase 1 ingestion pipeline for one document."""
    run_ingest_cli(path)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
