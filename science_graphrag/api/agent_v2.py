"""Agent query API v2: compatibility facade (router + digest helpers).

Implementation lives in :mod:`science_graphrag.api.agent_v2_modules.agent_query_router`.
"""

from __future__ import annotations

from science_graphrag.api.agent_v2_modules.agent_query_router import (
    normalize_history_digest_input,
    router,
)

__all__ = ["normalize_history_digest_input", "router"]
