"""Second-stage grounded LLM answer helper."""

from __future__ import annotations

from typing import Any

from openai import OpenAI

from science_graphrag.config import Settings


def _try_query_answer_llm(
    question: str,
    citations: list[dict[str, Any]],
    settings: Settings,
) -> tuple[str | None, dict[str, Any]]:
    if not settings.query_answer_llm_enabled:
        return None, {}
    api_key = settings.extraction_llm_api_key
    if not api_key:
        return None, {"skipped": True, "reason": "no_api_key"}

    ctx_lines: list[str] = []
    for idx, citation in enumerate(citations[:10], start=1):
        excerpt = (citation.get("excerpt") or "").strip()
        if not excerpt:
            continue
        meta: list[str] = []
        if citation.get("section_path"):
            meta.append(f"section={citation['section_path']}")
        if citation.get("chunk_fingerprint"):
            meta.append(f"chunk={citation['chunk_fingerprint']}")
        ctx_lines.append(f"[{idx}] ({', '.join(meta) if meta else 'excerpt'}) {excerpt}")
    if not ctx_lines:
        return None, {"skipped": True, "reason": "no_citation_text"}

    system = (
        "You are a scientific assistant. Answer ONLY using the numbered excerpts. "
        "If excerpts are insufficient, say so briefly. Do not invent citations, DOIs, "
        "or facts that are not supported by the excerpts."
    )
    user = f"Question:\n{question}\n\nExcerpts:\n" + "\n".join(ctx_lines)
    try:
        timeout = min(float(settings.extraction_llm_timeout_seconds), 120.0)
        client = OpenAI(
            api_key=api_key,
            base_url=settings.extraction_llm_base_url,
            timeout=timeout,
        )
        resp = client.chat.completions.create(
            model=settings.extraction_llm_model,
            temperature=float(settings.query_answer_llm_temperature),
            max_tokens=int(settings.query_answer_llm_max_tokens),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            return None, {"error": "empty_llm_response"}
        return text, {"model": settings.extraction_llm_model}
    except Exception as exc:  # noqa: BLE001
        return None, {"error": f"{type(exc).__name__}: {exc}"}
