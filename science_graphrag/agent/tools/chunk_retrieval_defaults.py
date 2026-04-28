"""Shared defaults for agent-facing Qdrant chunk retrieval (idea_search vs paper_quote_search)."""

from __future__ import annotations

# Keep idea_search and paper_quote_search aligned unless product explicitly diverges.
DEFAULT_AGENT_CHUNK_TOP_K = 5
MAX_AGENT_CHUNK_TOP_K = 24


def normalize_agent_retrieval_query(text: str) -> str:
    """Strip and collapse whitespace for embedding queries (idea_search + paper_quote_search)."""

    q = (text or "").strip()
    if not q:
        return ""
    return " ".join(q.split())
