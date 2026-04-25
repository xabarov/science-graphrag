"""Optional admin gate for sensitive API routers (benchmark, settings)."""

from __future__ import annotations

from fastapi import Header, HTTPException

from science_graphrag import config as _config


def require_admin_if_configured(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")
) -> None:
    """If ``SCIENCE_GRAPHRAG_ADMIN_API_KEY`` is set, require matching ``X-Admin-Key`` header."""

    settings = _config.get_settings()
    expected = (settings.admin_api_key or "").strip()
    if not expected:
        return
    got = (x_admin_key or "").strip()
    if got != expected:
        raise HTTPException(status_code=403, detail="admin_key_required")
