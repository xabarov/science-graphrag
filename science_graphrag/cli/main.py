from __future__ import annotations

from pathlib import Path

import typer

from science_graphrag.config import get_settings
from science_graphrag.ingestion.pipeline import run_ingest_cli
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
