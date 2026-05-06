"""Shared snapshot helpers for settings service."""

from __future__ import annotations

import os
import sys
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from science_graphrag.config import Settings


def build_diagnostics_snapshot() -> dict[str, Any]:
    """Build read-only runtime diagnostics payload."""
    try:
        app_version = metadata.version("science-graphrag")
    except metadata.PackageNotFoundError:
        app_version = None
    git_commit = (
        os.getenv("SCIENCE_GRAPHRAG_GIT_COMMIT")
        or os.getenv("CI_COMMIT_SHA")
        or os.getenv("GIT_COMMIT_SHA")
    )
    return {
        "app_version": app_version or "unknown",
        "python_version": (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        ),
        "in_docker": Path("/.dockerenv").is_file(),
        "git_commit": git_commit,
    }


def settings_auth_required() -> bool:
    return os.getenv("SCIENCE_GRAPHRAG_SETTINGS_AUTH_REQUIRED", "false").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def build_security_snapshot(base_settings: Settings) -> dict[str, Any]:
    """Build read-only settings/auth snapshot."""
    return {
        "admin_api_key_configured": bool((base_settings.admin_api_key or "").strip()),
        "settings_auth_required": settings_auth_required(),
    }


def resolve_ingestion_fields(
    ingestion_cfg: dict[str, Any], base_settings: Settings
) -> tuple[int, bool]:
    """Return resolved upload MB and claims flag (same rules as snapshot)."""
    raw_upload_mb = ingestion_cfg.get("max_file_size_mb")
    try:
        persisted_upload_mb = int(raw_upload_mb) if raw_upload_mb is not None else None
    except (TypeError, ValueError):
        persisted_upload_mb = None
    if persisted_upload_mb is not None:
        persisted_upload_mb = max(1, min(2048, persisted_upload_mb))
    raw_claims_enabled = ingestion_cfg.get("claims_extraction_enabled")
    if isinstance(raw_claims_enabled, bool):
        persisted_claims_enabled = raw_claims_enabled
    else:
        persisted_claims_enabled = None
    resolved_upload_mb = (
        persisted_upload_mb
        if persisted_upload_mb is not None
        else int(base_settings.workspace_upload_max_file_size_mb)
    )
    resolved_upload_mb = max(1, min(2048, resolved_upload_mb))
    resolved_claims_enabled = (
        persisted_claims_enabled
        if persisted_claims_enabled is not None
        else bool(base_settings.claims_extraction_enabled)
    )
    return resolved_upload_mb, resolved_claims_enabled
