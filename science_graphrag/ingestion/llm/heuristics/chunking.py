"""Chunking helpers for references batching."""

from __future__ import annotations

from science_graphrag.ingestion.stages.references import split_reference_entries


def reference_chunks(ref_text: str, batch_size: int) -> list[str]:
    synthetic_text = f"## References\n\n{ref_text}"
    entries = split_reference_entries(synthetic_text)
    if not entries:
        return [ref_text] if ref_text.strip() else []
    chunks: list[str] = []
    for i in range(0, len(entries), max(1, batch_size)):
        group = entries[i : i + batch_size]
        chunks.append("\n".join(entry.strip() for entry in group if entry).strip())
    return [chunk for chunk in chunks if chunk]


def reference_chunk_groups(ref_text: str, batch_size: int) -> list[list[str]]:
    synthetic_text = f"## References\n\n{ref_text}"
    entries = split_reference_entries(synthetic_text)
    if not entries:
        return [[ref_text]] if ref_text.strip() else []
    step = max(1, batch_size)
    return [entries[i : i + step] for i in range(0, len(entries), step)]
