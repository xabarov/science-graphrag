"""Public, non-secret hints for lightweight UI onboarding."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from science_graphrag.config import get_settings

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/setup-hints")
def get_setup_hints() -> dict[str, Any]:
    """Return booleans only (no secrets) for first-run LLM guidance."""

    settings = get_settings()
    extraction_ok = bool((settings.extraction_llm_api_key or "").strip())
    vl_effective = bool((settings.resolved_vl_api_key or "").strip())
    return {
        "needs_initial_setup": not extraction_ok,
        "llm_api_key_configured": extraction_ok,
        "vl_api_key_configured": vl_effective,
    }
