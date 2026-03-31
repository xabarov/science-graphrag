#!/usr/bin/env python3
"""
Build a layer-1 benchmark fixture (article.md) from a scholarly PDF via pypdf text.

Uses the same text path as production ``extract_text_from_pdf`` (no VL). Output is
structured markdown: # title, authors, ## Abstract, ## Body, ## References — so
``extract_references`` and benchmarks match the rest of the suite.

Example:
  .venv/bin/python scripts/build_real_pdf_layer1_fixture.py \\
    --pdf /path/to/RetinaNet.pdf \\
    --out tests/fixtures/benchmarks/layer1/retinanet_focal_realpdf
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Repo root on PYTHONPATH when run as ``python scripts/...`` from cwd root.
from science_graphrag.ingestion.normalize import normalize_text
from science_graphrag.ingestion.pdf import extract_text_from_pdf
from science_graphrag.ingestion.stages.references import extract_references


def _authors_title_pre_abstract(pre: str) -> tuple[str, str]:
    lines = [ln.rstrip() for ln in pre.splitlines()]
    nonempty = [ln.strip() for ln in lines if ln.strip()]
    if not nonempty:
        return "Untitled", ""
    title = nonempty[0]
    author_lines: list[str] = []
    for ln in nonempty[1:]:
        low = ln.lower()
        if re.search(r"^figure\s*\d", low):
            break
        if "ce(pt)" in low or "fl(pt)" in low:
            break
        if re.match(r"^[\d\s.]+$", ln) and len(ln) < 30:
            continue
        if "well-classi" in low:
            break
        if "probability of ground truth" in low:
            break
        if "@" in ln:
            break
        author_lines.append(ln)
        if "facebook ai" in low:
            break
        if "adelaide" in low or ("australia" in low and "university" in low):
            break
        if "brain team" in low or "google research" in low:
            break
        if len(author_lines) >= 8:
            break
    return title, "\n".join(author_lines)


def _trim_abstract_chunk(chunk: str) -> tuple[str, str]:
    lines = chunk.split("\n")
    url_idx = None
    for i, ln in enumerate(lines):
        if re.search(r"https?://|tinyurl\.com", ln, re.I):
            url_idx = i
            break
    if url_idx is not None:
        return (
            "\n".join(lines[: url_idx + 1]).strip(),
            "\n".join(lines[url_idx + 1 :]).strip(),
        )
    # Springer-style or similar: abstract paragraph then "Keywords:" before §1
    for i, ln in enumerate(lines):
        if re.match(r"(?i)^keywords:\s*", ln.strip()):
            return "\n".join(lines[:i]).strip(), "\n".join(lines[i:]).strip()
    for i, ln in enumerate(lines):
        if re.match(r"(?i)^\s*figure\s*\d", ln):
            return "\n".join(lines[:i]).strip(), "\n".join(lines[i:]).strip()
    return chunk.strip(), ""


def _split_head_at_abstract(head: str) -> tuple[str, str]:
    """
    Return (text_before_abstract, text_starting_at_abstract_body).

    Supports a standalone ``Abstract`` line (CVPR-style) or inline ``Abstract.`` / ``ABSTRACT.``
    (Springer / arXiv-style).
    """

    m_line = re.search(r"(?im)^\s*abstract\s*$", head, flags=re.MULTILINE)
    if m_line:
        pre = head[: m_line.start()]
        after = head[m_line.end() :].lstrip("\n")
        return pre, after
    m_inline = re.search(r"(?im)^abstract\.\s+", head, flags=re.MULTILINE)
    if m_inline:
        pre = head[: m_inline.start()]
        after = head[m_inline.end() :]
        return pre, after
    # Inline "Abstract We propose ..." (ECCV/CVPR one-line abstract label)
    m_inline_word = re.search(r"(?im)^\s*abstract\s+(?=\S)", head)
    if m_inline_word:
        pre = head[: m_inline_word.start()]
        after = head[m_inline_word.end() :].lstrip()
        return pre, after
    # IEEE-style "Abstract— ..." / "Abstract- ..."
    m_ieee = re.search(r"(?im)^\s*abstract[—\-]\s*", head)
    if m_ieee:
        pre = head[: m_ieee.start()]
        after = head[m_ieee.end() :]
        return pre, after
    raise ValueError(
        "No 'Abstract' block found (expected standalone Abstract, Abstract., "
        "Abstract—, or inline Abstract <word>)"
    )


def _match_introduction_heading(after_abs: str) -> re.Match[str] | None:
    """Locate the first ``1 Introduction`` / ``1 INTRODUCTION`` heading in body text."""

    mintro = re.search(r"(?im)^\s*1\.\s*Introduction\s*$", after_abs, re.MULTILINE)
    if not mintro:
        mintro = re.search(r"(?im)^\s*1\s+Introduction\s*$", after_abs, re.MULTILINE)
    if not mintro:
        mintro = re.search(
            r"(?im)^\s*1\s+I\s+N\s*T\s*R\s*O\s*D\s*U\s*C\s*T\s*I\s*O\s*N\s*$",
            after_abs,
            re.MULTILINE,
        )
    if not mintro:
        mintro = re.search(r"(?im)^\s*1\s+INTRODUCTION\s*$", after_abs, re.MULTILINE)
    return mintro


def _assemble_benchmark_markdown(
    *,
    title: str,
    authors: str,
    abstract: str,
    body: str,
    ref_tail: str,
) -> str:
    """Join title/authors/abstract/body/references into layer-1 fixture markdown."""

    parts = [
        f"# {title}",
        "",
        authors,
        "",
        "## Abstract",
        "",
        abstract,
        "",
        "## Body",
        "",
        body,
        "",
        "## References",
        "",
        ref_tail.strip(),
    ]
    return "\n".join(parts)


def pdf_to_article_md(pdf: Path, *, body_max_chars: int = 48_000) -> str:
    """Normalize PDF text into benchmark-shaped markdown (title, abstract, body, references)."""
    norm = normalize_text(extract_text_from_pdf(pdf))
    mref = re.search(r"(?im)^\s*references\s*\n", norm)
    if not mref:
        mref = re.search(r"(?im)^\s*bibliography\s*\n", norm)
    if not mref:
        raise ValueError("No 'References' / 'Bibliography' section found in extracted text")
    head = norm[: mref.start()]
    ref_tail = norm[mref.end() :]
    pre, after_abs = _split_head_at_abstract(head)
    title, authors = _authors_title_pre_abstract(pre)
    mintro = _match_introduction_heading(after_abs)
    if not mintro:
        raise ValueError("No '1. Introduction' / '1 Introduction' / '1 INTRODUCTION' heading found")
    chunk = after_abs[: mintro.start()]
    abstract, mid = _trim_abstract_chunk(chunk)
    body = (mid + "\n\n" + after_abs[mintro.start() :].strip()).strip()
    if len(body) > body_max_chars:
        body = (
            body[:body_max_chars]
            + "\n\n[... truncated for benchmark fixture size — see script body_max_chars ...]\n"
        )
    return _assemble_benchmark_markdown(
        title=title,
        authors=authors,
        abstract=abstract,
        body=body,
        ref_tail=ref_tail,
    )


def _suggest_gold_stub(case_id: str, title: str, abstract: str, article_md: str) -> dict:
    refs = extract_references(article_md)
    n = len(refs)
    arxiv_ids = []
    seen: set[str] = set()
    for r in refs:
        if r.arxiv_id and r.arxiv_id not in seen:
            seen.add(r.arxiv_id)
            arxiv_ids.append(r.arxiv_id)
    dois = []
    seen_d: set[str] = set()
    for r in refs:
        if r.doi and r.doi not in seen_d:
            seen_d.add(r.doi)
            dois.append(r.doi)
    prefix = re.sub(r"\s+", " ", abstract.replace("\n", " ").strip())[:72]
    return {
        "case_id": case_id,
        "schema_version": 1,
        "description": "Real CV paper: PDF→text (pypdf) → structured MD; noisy but realistic.",
        "work_metadata": {
            "title": title,
            "publication_year": None,
            "abstract_prefix": prefix,
            "doi": None,
            "arxiv_id": None,
            "venue_name": None,
            "work_type": None,
        },
        "authorships": [],
        "references": {
            "expected_count": n,
            "min_count": max(0, n - 8) if n else 0,
            "notes": (
                "Heuristic extract_references counts on this MD; "
                "PDF hyphenation may shift totals."
            ),
            "sample_arxiv_ids": arxiv_ids[:12],
            "sample_dois": dois[:8],
        },
        "graph_expectations": {
            "min_cites": 0,
            "max_cites": min(n + 10, 80),
            "expected_cited_arxiv_ids": arxiv_ids[:5],
            "max_duplicate_work_fingerprints": 8,
        },
    }


def main() -> int:
    """CLI: write article.md + gold.json stub under ``--out``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="Fixture directory to create")
    parser.add_argument("--case-id", required=True, help="Stable id for gold.json")
    parser.add_argument("--body-max-chars", type=int, default=48_000)
    args = parser.parse_args()
    if not args.pdf.is_file():
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    md = pdf_to_article_md(args.pdf, body_max_chars=args.body_max_chars)
    (args.out / "article.md").write_text(md, encoding="utf-8")
    title = md.split("\n", 1)[0].lstrip("# ").strip()
    abs_m = re.search(
        r"## Abstract\s*\n+(.*?)\n+\s*## Body",
        md,
        re.DOTALL,
    )
    abstract = abs_m.group(1).strip() if abs_m else ""
    stub = _suggest_gold_stub(args.case_id, title, abstract, md)
    gold_path = args.out / "gold.json"
    gold_path.write_text(json.dumps(stub, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out / 'article.md'} ({len(md)} chars)")
    print(f"Wrote {gold_path} — fill in authorships[] manually for strict name checks.")
    print(f"Heuristic reference count: {stub['references']['expected_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
