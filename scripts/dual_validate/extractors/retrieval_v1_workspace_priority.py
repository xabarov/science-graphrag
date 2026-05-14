"""Spot-check priority rules for ``workspace_scoped_live`` retrieval dual-validate layer."""


def classify_workspace_scoped_spot_check(
    *,
    metrics_required: dict[str, float],
    metrics_all: dict[str, float],
    boundary_violations: int,
    real_violations_predicted: int,  # noqa: ARG001 — kept for API symmetry with extractor
    a_empty_negative_case: bool = False,
    b_empty: bool = False,
) -> tuple[str, str]:
    """Return ``(spot_check_priority, rationale)`` for workspace-scoped packs."""
    if boundary_violations > 0:
        return (
            "high",
            f"B proposed {boundary_violations} out-of-scope corpus_work_id(s) — workspace boundary leak",
        )
    if a_empty_negative_case:
        if b_empty:
            return (
                "low",
                "negative case: B also returned an empty expected_corpus_work_ids set",
            )
        return (
            "high",
            "negative case: B proposed citations where gold expects abstain",
        )
    if metrics_required["recall"] >= 0.9 and metrics_all["precision"] >= 0.7:
        return (
            "low",
            f"required-recall={metrics_required['recall']:.2f}, precision={metrics_all['precision']:.2f}",
        )
    if metrics_required["recall"] >= 0.5 and metrics_all["precision"] >= 0.5:
        return (
            "medium",
            f"required-recall={metrics_required['recall']:.2f}, precision={metrics_all['precision']:.2f}",
        )
    return (
        "high",
        f"required-recall={metrics_required['recall']:.2f}, precision={metrics_all['precision']:.2f} (gate)",
    )


__all__ = ["classify_workspace_scoped_spot_check"]
