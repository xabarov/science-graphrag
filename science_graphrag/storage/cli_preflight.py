"""Shared CLI checks for scripts that require S3/MinIO."""

from __future__ import annotations

import sys
from typing import TextIO

from science_graphrag.config import Settings


def settings_or_exit_for_object_storage_cli() -> tuple[Settings, int | None]:
    """
    Load settings and validate object storage is enabled.

    Returns ``(settings, None)`` on success, or ``(settings, 1)`` when the CLI must exit.
    """
    settings = Settings()
    return settings, exit_if_object_storage_disabled(settings)


def exit_if_object_storage_disabled(
    settings: Settings,
    *,
    stream: TextIO = sys.stderr,
) -> int | None:
    """
    Return ``1`` if object storage is not enabled (caller should ``sys.exit``).

    Returns ``None`` when OK.
    """
    if not settings.object_storage_enabled:
        print(
            "error: SCIENCE_GRAPHRAG_OBJECT_STORAGE_ENABLED=true required",
            file=stream,
        )
        return 1
    return None
