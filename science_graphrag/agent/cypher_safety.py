from __future__ import annotations

import re

FORBIDDEN_TOKENS = (
    "CREATE",
    "MERGE",
    "DELETE",
    "DETACH",
    "SET",
    "REMOVE",
    "DROP",
    "LOAD CSV",
    "CALL DBMS",
    "APOC.CREATE",
    "APOC.MERGE",
    "APOC.DELETE",
)

ALLOWED_LABELS = {
    "Work",
    "Author",
    "Authorship",
    "Institution",
    "Venue",
    "Method",
    "Dataset",
    "Workspace",
    "Claim",
    "Evidence",
    "Concept",
    "ResearchTopic",
}


class CypherNotAllowedError(ValueError):
    pass


def validate_readonly_cypher(query: str, *, max_limit: int = 200) -> None:
    raw = (query or "").strip()
    if not raw:
        raise CypherNotAllowedError("empty_query")
    upper = raw.upper()
    for token in FORBIDDEN_TOKENS:
        if token in upper:
            raise CypherNotAllowedError(f"forbidden_token:{token}")

    for label in re.findall(r":([A-Za-z_][A-Za-z0-9_]*)", raw):
        if label not in ALLOWED_LABELS:
            raise CypherNotAllowedError(f"unknown_label:{label}")

    m = re.search(r"\bLIMIT\s+(\d+)\b", upper)
    if m and int(m.group(1)) > max_limit:
        raise CypherNotAllowedError("limit_too_high")
