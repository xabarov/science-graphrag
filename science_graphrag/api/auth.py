"""Minimal auth helpers for protected API routes."""

from __future__ import annotations

import os

from fastapi import Header, HTTPException, status


def _settings_access_enabled() -> bool:
    return os.getenv("SCIENCE_GRAPHRAG_SETTINGS_AUTH_REQUIRED", "false").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def require_settings_access(authorization: str | None = Header(default=None)) -> str:
    """Require a bearer token for settings routes when the feature flag is enabled."""
    if not _settings_access_enabled():
        return "local-admin"
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="settings_auth_required",
        )
    token = authorization.removeprefix("Bearer ").strip()
    expected = os.getenv("SCIENCE_GRAPHRAG_SETTINGS_BEARER_TOKEN", "").strip()
    if not expected or token != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="settings_access_denied",
        )
    return "authenticated-user"
