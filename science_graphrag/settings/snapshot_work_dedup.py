"""Work dedup effective snapshot (read-only operator view)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from science_graphrag.config import Settings


def build_work_dedup_snapshot(
    *, base_settings: Settings, merged_settings: Settings
) -> dict[str, Any]:
    """Build work/author dedup effective fields for the settings UI."""
    q_work = merged_settings.qdrant_work_embeddings_collection
    q_author = merged_settings.qdrant_author_embeddings_collection
    return {
        "effective": {
            "qdrant_work_embeddings_collection": q_work,
            "qdrant_author_embeddings_collection": q_author,
            "work_dedup_sim_low": float(base_settings.work_dedup_sim_low),
            "work_dedup_sim_high": float(base_settings.work_dedup_sim_high),
            "work_dedup_max_candidates": int(base_settings.work_dedup_max_candidates),
            "work_dedup_llm_mode": str(base_settings.work_dedup_llm_mode),
            "work_dedup_llm_timeout_s": float(merged_settings.work_dedup_llm_timeout_s),
            "author_dedup_sim_low": float(base_settings.author_dedup_sim_low),
            "author_dedup_sim_high": float(base_settings.author_dedup_sim_high),
            "author_dedup_max_candidates": int(base_settings.author_dedup_max_candidates),
            "author_dedup_llm_timeout_s": float(merged_settings.author_dedup_llm_timeout_s),
        }
    }
