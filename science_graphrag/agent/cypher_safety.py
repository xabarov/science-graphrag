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


def _forbidden_token_present(query: str, token: str) -> bool:
    """Match Cypher keywords as whole words (labels like ``Dataset`` must not trip ``SET``)."""

    if token == "LOAD CSV":
        return re.search(r"\bLOAD\s+CSV\b", query, flags=re.IGNORECASE) is not None
    if token == "CALL DBMS":
        return re.search(r"\bCALL\s+DBMS\b", query, flags=re.IGNORECASE) is not None
    if "." in token:
        return re.search(rf"\b{re.escape(token)}\b", query, flags=re.IGNORECASE) is not None
    return re.search(rf"\b{re.escape(token)}\b", query, flags=re.IGNORECASE) is not None


def validate_readonly_cypher(query: str, *, max_limit: int = 200) -> None:
    raw = (query or "").strip()
    if not raw:
        raise CypherNotAllowedError("empty_query")
    upper = raw.upper()
    for token in FORBIDDEN_TOKENS:
        if _forbidden_token_present(raw, token):
            raise CypherNotAllowedError(f"forbidden_token:{token}")

    # Strip relationship patterns in square brackets so `:REL_TYPE`
    # does not get validated as a node label.
    node_scope = re.sub(r"\[[^\]]*\]", "", raw)
    for label in re.findall(r":([A-Za-z_][A-Za-z0-9_]*)", node_scope):
        if label not in ALLOWED_LABELS:
            raise CypherNotAllowedError(f"unknown_label:{label}")

    m = re.search(r"\bLIMIT\s+(\d+)\b", upper)
    if m and int(m.group(1)) > max_limit:
        raise CypherNotAllowedError("limit_too_high")
