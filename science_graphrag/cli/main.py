from __future__ import annotations

import typer

from science_graphrag.cli.config_commands import register as register_config_commands
from science_graphrag.cli.dedup_commands import register as register_dedup_commands
from science_graphrag.cli.ingest_commands import register as register_ingest_commands
from science_graphrag.cli.neo4j_commands import register as register_neo4j_commands
from science_graphrag.cli.qdrant_commands import register as register_qdrant_commands
from science_graphrag.utils.project_logging import configure_logging

app = typer.Typer(no_args_is_help=True, help="science-graphrag CLI")


@app.callback()
def _root() -> None:
    """Scholarly GraphRAG — ingestion and graph backbone."""
    configure_logging()


register_qdrant_commands(app)
register_config_commands(app)
register_ingest_commands(app)
register_dedup_commands(app)
register_neo4j_commands(app)


@app.command("merge-catalog-audit")
def merge_catalog_audit_cmd() -> None:
    """Author/institution merge catalog — policy checklist (Wave H2 scaffold).

    Full clients (Crossref/ORCID/ROR) are not wired here yet; this command prints
    the canonical doc pointer for operators.
    """

    typer.echo(
        "merge-catalog-audit: no external API calls in this build.\n"
        "See docs/specs/merge-catalog-wave-h.md and docs/adr/009-author-institution-merge-catalog.md"
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
