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
    event: str | None = None,
    pages: str | None = None,
) -> str:
    """Single entry approximating journal / conference / preprint (RU-friendly, minimal GOST)."""
    auth = ", ".join(a.strip() for a in authors if (a or "").strip()) or "Без указания авторов"
    ttl = (title or "").strip() or "Без названия"
    ven = (venue or "").strip()
    ev = (event or "").strip()
    yr = str(year) if year is not None else ""
    d = (doi or "").strip()
    pg = (pages or "").strip()
    parts = [f"{auth} {ttl}"]
    if ev:
        parts.append(f" // {ev}")
        if ven:
            parts.append(f", {ven}.")
        else:
            parts.append(".")
    elif ven:
        parts.append(f"// {ven}.")
    else:
        parts.append(".")
    if yr:
        parts.append(f" — {yr}.")
    if pg:
        parts.append(f" — С. {pg}.")
    if d:
        parts.append(f" — DOI: {d}.")
    return "".join(parts).strip()


def _coerce_year(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def build_entries_from_work_cards(rows: list[dict[str, Any]]) -> list[str]:
    """Each row: title, year, doi, authors (list[str]), venue, event, pages (optional)."""
    out: list[str] = []
    for row in rows:
        authors = list(row.get("authors") or [])
        if isinstance(authors, str):
            authors = [authors]
        v = row.get("venue")
        ev = row.get("event")
        v_str = str(v).strip() if v is not None and str(v).strip() else None
        ev_str = str(ev).strip() if ev is not None and str(ev).strip() else None
        pages_val = row.get("pages")
        pages = str(pages_val).strip() if pages_val is not None and str(pages_val).strip() else None
        out.append(
            format_gost_article_line(
                authors=authors,
                title=str(row.get("title") or ""),
                venue=v_str,
                year=_coerce_year(row.get("year")),
                doi=row.get("doi") if row.get("doi") is not None else None,
                event=ev_str,
                pages=pages,
            )
        )
    return out
