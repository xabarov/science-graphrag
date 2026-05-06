from __future__ import annotations

import typer

from science_graphrag.config import get_settings
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


def register(app: typer.Typer) -> None:
    """Register Neo4j-related CLI commands."""

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

