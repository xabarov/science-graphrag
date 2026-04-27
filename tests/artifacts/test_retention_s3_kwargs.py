"""Retention tagging helpers."""

from __future__ import annotations

from science_graphrag.artifacts.retention import RetentionClass, s3_put_object_retention_kwargs


def test_s3_put_object_retention_kwargs_shape() -> None:
    """Tagging string contains expected retention keys."""
    kw = s3_put_object_retention_kwargs(
        RetentionClass.EPHEMERAL_DIAGNOSTIC,
        diagnostic_kind="od",
        retention_hint_days=7,
    )
    assert "Tagging" in kw
    assert "retention_class=ephemeral_diagnostic" in kw["Tagging"]
    assert "diagnostic_kind=od" in kw["Tagging"]
    assert "retention_hint_days=7" in kw["Tagging"]
    assert kw["Metadata"]["retention-class"] == "ephemeral_diagnostic"
    assert kw["Metadata"]["retention-hint-days"] == "7"
