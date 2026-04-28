"""Short secret masking for settings UI and storage snapshots."""


def mask_short_secret(value: str | None) -> str | None:
    """Return a short redacted form suitable for UI (not cryptographic)."""

    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * max(4, len(value) - 8)}{value[-4:]}"


__all__ = ["mask_short_secret"]
