"""Shared defaults for agent-facing Qdrant chunk retrieval (idea_search vs paper_quote_search).

Snippet length policy:
- ``AGENT_CHUNK_SNIPPET_CHARS_IDEA_SEARCH`` — shorter previews because ``idea_search`` often returns
  many rows; keeps tool payloads smaller for the ReAct loop.
- ``AGENT_CHUNK_SNIPPET_CHARS_PAPER_QUOTE`` — longer row snippets for citation-oriented retrieval.
- ``AGENT_CHUNK_QUOTE_TEXT_MAX_CHARS`` — separate cap for ``quote_candidates`` verbatim text.
"""

from __future__ import annotations

# Keep idea_search and paper_quote_search aligned unless product explicitly diverges.
DEFAULT_AGENT_CHUNK_TOP_K = 5
MAX_AGENT_CHUNK_TOP_K = 24

# Trace previews in tool_parameters (observability; not full query text).
AGENT_TOOL_QUERY_TRACE_CHARS = 200
AGENT_TOOL_FIND_WORKS_QUERY_TRACE_CHARS = 240

# Chunk / quote text budgets returned to the model (LLM-facing tool payloads).
AGENT_CHUNK_SNIPPET_CHARS_IDEA_SEARCH = 240
AGENT_CHUNK_SNIPPET_CHARS_PAPER_QUOTE = 400
AGENT_CHUNK_QUOTE_TEXT_MAX_CHARS = 800

# Workspace one-line composition summaries (workspace_inspect blurb + summarize_workspace).
DEFAULT_WORKSPACE_COMPOSITION_SAMPLE_WORKS = 8
MAX_WORKSPACE_COMPOSITION_SAMPLE_WORKS = 15


def normalize_agent_retrieval_query(text: str) -> str:
    """Strip and collapse whitespace for embedding queries (idea_search + paper_quote_search)."""

    q = (text or "").strip()
    if not q:
        return ""
    return " ".join(q.split())


__all__ = [
    "AGENT_CHUNK_QUOTE_TEXT_MAX_CHARS",
    "AGENT_CHUNK_SNIPPET_CHARS_IDEA_SEARCH",
    "AGENT_CHUNK_SNIPPET_CHARS_PAPER_QUOTE",
    "AGENT_TOOL_FIND_WORKS_QUERY_TRACE_CHARS",
    "AGENT_TOOL_QUERY_TRACE_CHARS",
    "DEFAULT_AGENT_CHUNK_TOP_K",
    "DEFAULT_WORKSPACE_COMPOSITION_SAMPLE_WORKS",
    "MAX_AGENT_CHUNK_TOP_K",
    "MAX_WORKSPACE_COMPOSITION_SAMPLE_WORKS",
    "normalize_agent_retrieval_query",
]
