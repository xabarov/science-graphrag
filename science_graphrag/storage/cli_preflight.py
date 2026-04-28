"""Shared CLI checks for scripts that require S3/MinIO."""

from __future__ import annotations

import sys

from pydantic import ValidationError

from science_graphrag.config import Settings


def settings_or_exit_for_object_storage_cli() -> tuple[Settings | None, int | None]:
    """
    Load settings (S3 credentials are mandatory).

    Returns ``(settings, None)`` on success, or ``(None, 1)`` when Settings validation fails.
    """
    try:
        return Settings(), None
    except (ValidationError, ValueError, OSError) as exc:
        print(f"error: invalid settings ({exc})", file=sys.stderr)
        return None, 1
