"""Institution node helpers for graph write stage."""

from __future__ import annotations

import uuid
from typing import Any

from science_graphrag.ingestion.enrichment.ror import lookup_ror_id_optional


def institution_nodes_from_authorships(
    authorships: list[Any],
    settings: Any,
) -> list[tuple[str, str, str | None]]:
    """Build `(institution_id, institution_name, ror_id)` tuples from authorships."""
    nodes: list[tuple[str, str, str | None]] = []
    for authorship in authorships:
        affiliation = next((value for value in authorship.raw_affiliations if value.strip()), None)
        if not affiliation:
            continue
        clean = affiliation.strip()
        inst_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "institution:" + clean.lower()))
        ror_id: str | None = None
        if settings.ror_lookup_enabled:
            ror_id = lookup_ror_id_optional(clean, settings.openalex_mailto)
        nodes.append((inst_id, clean, ror_id))
    return nodes
