"""Section-aware Markdown chunking for retrieval with deterministic fingerprints."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


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


def chunk_document_for_retrieval(
    text: str,
    *,
    target_tokens: int = 1200,
    overlap_tokens: int = 140,
) -> list[DocumentChunk]:
    """
    Build section-aware chunks over normalized markdown.
    """
    if not text.strip():
        return []

    all_chunks: list[DocumentChunk] = []
    global_idx = 0
    for section_path, start, _end, block in _heading_sections(text):
        section_chunks, global_idx = _chunk_section_body(
            section_path=section_path,
            block=block,
            block_start=start,
            target_tokens=target_tokens,
            overlap_tokens=overlap_tokens,
            global_index_start=global_idx,
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
