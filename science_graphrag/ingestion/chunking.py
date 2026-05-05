"""Section-aware Markdown chunking for retrieval with deterministic fingerprints."""

from __future__ import annotations

import functools
import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from science_graphrag.config import Settings

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

_CHUNKING_ENGINES = frozenset({"legacy", "chonkie_recursive"})
DEFAULT_CHUNKING_ENGINE = "chonkie_recursive"


def approx_tokens(text: str) -> int:
    """Rough token count without tiktoken (~4 chars per token for English prose)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _normalize_for_fingerprint(text: str) -> str:
    t = unicodedata.normalize("NFKC", text)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


@dataclass(slots=True)
class DocumentChunk:  # pylint: disable=too-many-instance-attributes
    """Retrieval / provenance unit for one document."""

    chunk_fingerprint: str
    section_path: str
    text: str
    start_offset: int
    end_offset: int
    overlap_prev: bool = False
    overlap_next: bool = False
    chunk_index: int = 0
    index_in_section: int = 0


def _fingerprint(section_path: str, norm_body: str, index_in_section: int) -> str:
    raw = f"{section_path}\x00{norm_body}\x00{index_in_section}".encode()
    return hashlib.sha256(raw).hexdigest()


def _heading_sections(text: str) -> list[tuple[str, int, int, str]]:
    """
    Split into (section_path, start, end, block_text) where block includes heading line(s)
    and content until the next heading of same or higher level (smaller # count).
    """
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return [("(document)", 0, len(text), text)]

    sections: list[tuple[str, int, int, str]] = []
    preamble_end = matches[0].start()
    if preamble_end > 0:
        sections.append(("(preamble)", 0, preamble_end, text[:preamble_end]))

    stack: list[tuple[int, str]] = []

    for i, m in enumerate(matches):
        level = len(m.group(1))
        title = m.group(2).strip()
        start = m.start()
        end = len(text)
        for j in range(i + 1, len(matches)):
            next_level = len(matches[j].group(1))
            if next_level <= level:
                end = matches[j].start()
                break
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        path = " / ".join(t for _, t in stack)
        sections.append((path, start, end, text[start:end]))
    return sections


def _overlap_tail(s: str, overlap_tokens: int) -> str:
    if not s or overlap_tokens <= 0:
        return ""
    max_chars = overlap_tokens * 4
    if len(s) <= max_chars:
        return s.strip()
    tail = s[-max_chars:]
    br = tail.find("\n\n")
    if 0 < br < len(tail) - 20:
        tail = tail[br + 2 :]
    return tail.strip()


def _paragraphs(block: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", block) if p.strip()]


def _paragraph_starts(block: str, paragraphs: list[str]) -> list[int]:
    starts: list[int] = []
    cursor = 0
    for para in paragraphs:
        pos = block.find(para, cursor)
        if pos < 0:
            pos = cursor
        starts.append(pos)
        cursor = pos + len(para)
    return starts


def _chunk_section_body(  # pylint: disable=too-many-arguments,too-many-locals,too-many-branches
    *,
    section_path: str,
    block: str,
    block_start: int,
    target_tokens: int,
    overlap_tokens: int,
    global_index_start: int,
) -> tuple[list[DocumentChunk], int]:
    paragraphs = _paragraphs(block)
    if not paragraphs:
        return [], global_index_start

    starts = _paragraph_starts(block, paragraphs)
    chunks: list[DocumentChunk] = []
    global_idx = global_index_start
    idx_in_sec = 0
    overlap_prefix = ""
    i = 0

    while i < len(paragraphs):
        acc_indices: list[int] = []
        acc_texts: list[str] = []
        if overlap_prefix:
            acc_texts.append(overlap_prefix)
        while i < len(paragraphs):
            candidate_texts = acc_texts + [paragraphs[i]]
            joined = "\n\n".join(candidate_texts)
            tok = approx_tokens(joined)
            only_overlap = bool(overlap_prefix) and acc_texts == [overlap_prefix]
            must_take = not acc_texts or only_overlap
            if tok <= target_tokens or must_take:
                acc_texts = candidate_texts
                acc_indices.append(i)
                i += 1
                if not must_take and tok >= target_tokens and acc_indices:
                    break
            else:
                break

        body_text = "\n\n".join(acc_texts)
        if not body_text.strip():
            break

        if acc_indices:
            start_in_block = starts[acc_indices[0]]
            if overlap_prefix:
                start_in_block = max(0, start_in_block - len(overlap_prefix) - 2)
        else:
            start_in_block = 0

        abs_start = block_start + start_in_block
        abs_end = abs_start + len(body_text)
        norm_body = _normalize_for_fingerprint(body_text)
        fp = _fingerprint(section_path, norm_body, idx_in_sec)
        overlap_prev = bool(overlap_prefix)
        chunks.append(
            DocumentChunk(
                chunk_fingerprint=fp,
                section_path=section_path,
                text=body_text,
                start_offset=abs_start,
                end_offset=abs_end,
                overlap_prev=overlap_prev,
                overlap_next=False,
                chunk_index=global_idx,
                index_in_section=idx_in_sec,
            ),
        )
        global_idx += 1
        idx_in_sec += 1
        overlap_prefix = _overlap_tail(body_text, overlap_tokens)

    for j in range(len(chunks) - 1):
        if chunks[j + 1].overlap_prev:
            chunks[j].overlap_next = True

    return chunks, global_idx


@functools.lru_cache(maxsize=32)
def _cached_chonkie_recursive_chunker(
    recipe: str,
    lang: str,
    chunk_size: int,
    min_chars: int,
) -> Any:
    """Build a cached RecursiveChunker (character tokenizer; chunk_size ~ char budget)."""
    try:
        from chonkie import RecursiveChunker
    except ImportError as exc:  # pragma: no cover - guarded by dependency in pyproject
        raise ImportError(
            'chonkie is required for chunking_engine="chonkie_recursive" '
            '(install project dependencies: chonkie, jsonschema).',
        ) from exc
    return RecursiveChunker.from_recipe(
        name=recipe,
        lang=lang,
        tokenizer="character",
        chunk_size=chunk_size,
        min_characters_per_chunk=min_chars,
    )


def _chunk_section_body_chonkie(  # pylint: disable=too-many-arguments
    *,
    section_path: str,
    block: str,
    block_start: int,
    target_tokens: int,
    global_index_start: int,
    chonkie_recipe: str,
    chonkie_lang: str,
    chonkie_min_chars: int,
) -> tuple[list[DocumentChunk], int]:
    """
    Split one section block using Chonkie RecursiveChunker (markdown recipe).

    Character tokenizer chunk_size is aligned with legacy ``approx_tokens`` budget:
    ``max(min_chars, target_tokens * 4)`` characters per chunk (see runbook).
    Overlap between chunks is not injected here; ``overlap_prev`` / ``overlap_next`` stay false.
    """
    if not block.strip():
        return [], global_index_start

    chunk_size = max(chonkie_min_chars, target_tokens * 4)
    chunker = _cached_chonkie_recursive_chunker(
        chonkie_recipe.strip() or "markdown",
        (chonkie_lang or "en").strip() or "en",
        chunk_size,
        chonkie_min_chars,
    )
    raw = chunker.chunk(block)
    chunks: list[DocumentChunk] = []
    global_idx = global_index_start

    if not raw:
        norm_body = _normalize_for_fingerprint(block)
        fp = _fingerprint(section_path, norm_body, 0)
        chunks.append(
            DocumentChunk(
                chunk_fingerprint=fp,
                section_path=section_path,
                text=block,
                start_offset=block_start,
                end_offset=block_start + len(block),
                overlap_prev=False,
                overlap_next=False,
                chunk_index=global_idx,
                index_in_section=0,
            ),
        )
        return chunks, global_idx + 1

    for idx_in_sec, ch in enumerate(raw):
        s = int(ch.start_index)
        e = int(ch.end_index)
        body = block[s:e]
        if ch.text != body:
            body = ch.text
            pos = block.find(body, 0 if idx_in_sec == 0 else int(raw[idx_in_sec - 1].end_index))
            if pos < 0:
                pos = s
                e = pos + len(body)
            else:
                s = pos
                e = pos + len(body)
        abs_start = block_start + s
        abs_end = block_start + e
        norm_body = _normalize_for_fingerprint(body)
        fp = _fingerprint(section_path, norm_body, idx_in_sec)
        chunks.append(
            DocumentChunk(
                chunk_fingerprint=fp,
                section_path=section_path,
                text=body,
                start_offset=abs_start,
                end_offset=abs_end,
                overlap_prev=False,
                overlap_next=False,
                chunk_index=global_idx,
                index_in_section=idx_in_sec,
            ),
        )
        global_idx += 1

    return chunks, global_idx


def _normalize_chunking_engine(engine: str) -> str:
    key = (engine or DEFAULT_CHUNKING_ENGINE).strip().lower()
    if key not in _CHUNKING_ENGINES:
        raise ValueError(
            f"Unknown chunking engine {engine!r}; expected one of {sorted(_CHUNKING_ENGINES)}",
        )
    return key


def chunk_document_for_retrieval(
    text: str,
    *,
    target_tokens: int = 1200,
    overlap_tokens: int = 140,
    engine: str = DEFAULT_CHUNKING_ENGINE,
    chonkie_recipe: str = "markdown",
    chonkie_lang: str = "en",
    chonkie_min_characters_per_chunk: int = 24,
) -> list[DocumentChunk]:
    """
    Build section-aware chunks over normalized markdown.

    ``engine``:
    - ``legacy``: paragraph packing with ``overlap_tokens`` tail overlap.
    - ``chonkie_recursive``: Chonkie RecursiveChunker per section;
      ``overlap_tokens`` ignored for now.
    """
    if not text.strip():
        return []

    eng = _normalize_chunking_engine(engine)
    all_chunks: list[DocumentChunk] = []
    global_idx = 0

    for section_path, start, _end, block in _heading_sections(text):
        if eng == "legacy":
            section_chunks, global_idx = _chunk_section_body(
                section_path=section_path,
                block=block,
                block_start=start,
                target_tokens=target_tokens,
                overlap_tokens=overlap_tokens,
                global_index_start=global_idx,
            )
        else:
            section_chunks, global_idx = _chunk_section_body_chonkie(
                section_path=section_path,
                block=block,
                block_start=start,
                target_tokens=target_tokens,
                global_index_start=global_idx,
                chonkie_recipe=chonkie_recipe,
                chonkie_lang=chonkie_lang,
                chonkie_min_chars=chonkie_min_characters_per_chunk,
            )
        all_chunks.extend(section_chunks)

    if not all_chunks and text.strip():
        norm_body = _normalize_for_fingerprint(text)
        fp = _fingerprint("(document)", norm_body, 0)
        all_chunks.append(
            DocumentChunk(
                chunk_fingerprint=fp,
                section_path="(document)",
                text=text.strip(),
                start_offset=0,
                end_offset=len(text.strip()),
                overlap_prev=False,
                overlap_next=False,
                chunk_index=0,
                index_in_section=0,
            ),
        )

    for i, ch in enumerate(all_chunks):
        ch.chunk_index = i
    return all_chunks


def chunk_document_for_retrieval_from_settings(
    text: str,
    settings: "Settings",
) -> list[DocumentChunk]:
    """Chunk normalized markdown using ``settings`` chunking fields (single entry for ingest)."""
    return chunk_document_for_retrieval(
        text,
        target_tokens=settings.chunk_target_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
        engine=settings.chunking_engine,
        chonkie_recipe=settings.chunking_chonkie_recipe,
        chonkie_lang=settings.chunking_chonkie_lang,
        chonkie_min_characters_per_chunk=settings.chunking_chonkie_min_characters_per_chunk,
    )


def infer_chunk_kind_from_section_path(section_path: str | None, *, default: str = "body") -> str:
    """
    Coarse section bucket for hybrid retrieval / rerank (Wave Q).

    TODO: cited_work_ids / mentioned_method_ids on chunk payload require a later
    ``extract_in_text_citations`` pipeline stage (ontology roadmap §6.2).
    """

    sp = (section_path or "").lower()
    if "abstract" in sp or sp.strip() == "(preamble)":
        return "abstract"
    if any(k in sp for k in ("reference", "bibliograph")):
        return "references"
    if any(k in sp for k in ("method", "approach", "architecture", "model", "network")):
        return "method"
    if any(k in sp for k in ("experiment", "result", "evaluation", "implementation")):
        return "result"
    if any(k in sp for k in ("discussion", "conclusion")):
        return "discussion"
    return default


def dedupe_chunks_for_embedding(chunks: list[DocumentChunk]) -> list[DocumentChunk]:
    """Drop exact fingerprint duplicates (keep first order)."""
    seen: set[str] = set()
    out: list[DocumentChunk] = []
    for ch in chunks:
        if ch.chunk_fingerprint in seen:
            continue
        seen.add(ch.chunk_fingerprint)
        out.append(ch)
    for i, ch in enumerate(out):
        ch.chunk_index = i
    return out
