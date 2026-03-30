from __future__ import annotations

from pathlib import Path

import typer

from science_graphrag.config import get_settings
from science_graphrag.ingestion.pipeline import run_ingest_batch_cli, run_ingest_cli
from science_graphrag.storage.neo4j_store import Neo4jGraphStore

app = typer.Typer(no_args_is_help=True, help="science-graphrag CLI")


@app.callback()
def _root() -> None:
    """Scholarly GraphRAG — ingestion and graph backbone."""


@app.command("neo4j-wipe")
def neo4j_wipe_cmd() -> None:
    """Remove all nodes and relationships from the configured Neo4j database."""
    s = get_settings()
    neo = Neo4jGraphStore(s.neo4j_uri, s.neo4j_user, s.neo4j_password)
    try:
        neo.wipe_all()
    finally:
        neo.close()
    typer.echo("Neo4j database wiped.")


@app.command("ingest")
def ingest_cmd(
    path: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="PDF, .txt, or .md (markdown read as article text)",
    ),
) -> None:
    """Run Phase 1 ingestion pipeline for one document."""
    run_ingest_cli(path)


@app.command("ingest-corpus")
def ingest_corpus_cmd(
    directory: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Directory tree to scan for .pdf, .md, and .txt files",
    ),
    continue_on_error: bool = typer.Option(
        False,
        "--continue-on-error",
        help="Log failures and continue with remaining files",
    ),
) -> None:
    """Batch-ingest a corpus directory and print Work-level dedup audit for Neo4j."""

    run_ingest_batch_cli(directory, continue_on_error=continue_on_error)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
