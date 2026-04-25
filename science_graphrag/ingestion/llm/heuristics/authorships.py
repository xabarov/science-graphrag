"""Helpers for authorship stage fallback decisions."""

from __future__ import annotations

from science_graphrag.domain.models import AuthorshipDraft
from science_graphrag.ingestion.llm.schemas import AuthorshipsLLM


def authorships_from_llm(parsed: AuthorshipsLLM) -> list[AuthorshipDraft]:
    out: list[AuthorshipDraft] = []
    for item in parsed.authors:
        name = (item.name or "").strip()
        if not name:
            continue
        affiliations = [x.strip() for x in item.affiliations if x and str(x).strip()]
        out.append(
            AuthorshipDraft(
                author_position=len(out) + 1,
                author_raw_name=name,
                raw_affiliations=affiliations,
                is_corresponding=item.is_corresponding,
                email=(item.email or "").strip() or None,
            )
        )
        if len(out) >= 40:
            break
    return out


def llm_authorships_need_fallback(
    llm_authorships: list[AuthorshipDraft],
    heuristic_authorships: list[AuthorshipDraft],
) -> bool:
    if not llm_authorships:
        return True
    llm_affs = sum(1 for item in llm_authorships if item.raw_affiliations)
    heuristic_affs = sum(1 for item in heuristic_authorships if item.raw_affiliations)
    return llm_affs == 0 and heuristic_affs > 0
