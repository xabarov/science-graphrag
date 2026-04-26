"""Deterministic GOST-like bibliography lines (Wave A — minimal formatter)."""

from __future__ import annotations

from typing import Any


def format_gost_article_line(
    *,
    authors: list[str],
    title: str,
    venue: str | None,
    year: int | None,
    doi: str | None,
) -> str:
    """Single entry approximating journal article / preprint style (RU-friendly)."""
    auth = ", ".join(a.strip() for a in authors if (a or "").strip()) or "Без указания авторов"
    ttl = (title or "").strip() or "Без названия"
    ven = (venue or "").strip()
    yr = str(year) if year is not None else ""
    d = (doi or "").strip()
    parts = [f"{auth} {ttl}"]
    if ven:
        parts.append(f"// {ven}.")
    else:
        parts.append(".")
    if yr:
        parts.append(f" — {yr}.")
    if d:
        parts.append(f" — DOI: {d}.")
    return "".join(parts).strip()


def build_entries_from_work_cards(rows: list[dict[str, Any]]) -> list[str]:
    """Each row: title, year, doi, authors (list[str]), venue (optional)."""
    out: list[str] = []
    for row in rows:
        authors = list(row.get("authors") or [])
        if isinstance(authors, str):
            authors = [authors]
        out.append(
            format_gost_article_line(
                authors=authors,
                title=str(row.get("title") or ""),
                venue=row.get("venue"),
                year=row.get("year"),
                doi=row.get("doi"),
            )
        )
    return out
