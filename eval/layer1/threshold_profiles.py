"""Named threshold presets for layer-1 benchmarks (student vs curated gold)."""

from __future__ import annotations

from eval.layer1.spec import Layer1GoldSpec, Layer1QualityThresholds

# Tuned for Mistral student vs DeepSeek teacher gold: exact title/abstract often drift on PDF-MD.
# Smoke / CI: run extraction end-to-end without failing on reference count drift (heuristic PDF→MD).
CI_SMOKE_LAYER1_THRESHOLDS = Layer1QualityThresholds(
    require_title_match=True,
    require_abstract_prefix=True,
    require_reference_count_ok=False,
)

STUDENT_MISTRAL_LAYER1_THRESHOLDS = Layer1QualityThresholds(
    require_title_match=False,
    require_abstract_prefix=False,
    require_reference_count_ok=True,
    min_authorship_names_recall=0.55,
    min_authorship_names_f1=0.50,
    min_affiliations_f1=0.28,
    min_sample_arxiv_f1=0.45,
    min_sample_doi_f1=0.40,
    min_title_rouge_l=0.82,
    min_abstract_rouge_l=None,
    min_title_token_f1=0.82,
    min_authorship_names_difflib_macro=0.88,
)


def apply_layer1_threshold_profile(gold: Layer1GoldSpec, profile: str | None) -> Layer1GoldSpec:
    """Return a copy of gold with merged quality_thresholds for named profile."""

    if not profile or profile in ("none", "from_gold"):
        return gold
    if profile == "reporting_skip_f1_gates":
        # Keep gold-authored lists for metrics (names_f1, sample_arxiv_f1) but do not fail the
        # contract on min_* F1 gates yet — extractor is still being tuned against enriched gold.
        base = (
            gold.quality_thresholds.model_copy()
            if gold.quality_thresholds
            else Layer1QualityThresholds()
        )
        merged = base.model_dump()
        merged.update(
            {
                "min_authorship_names_f1": None,
                "min_sample_arxiv_f1": None,
                # PDF→MD hyphenation shifts reference counts; nightly reporting matches CI smoke
                # for this gate while still emitting count_ok / deltas in metrics.
                "require_reference_count_ok": False,
            }
        )
        return gold.model_copy(
            update={"quality_thresholds": Layer1QualityThresholds.model_validate(merged)}
        )
    if profile == "ci_smoke":
        return gold.model_copy(update={"quality_thresholds": CI_SMOKE_LAYER1_THRESHOLDS})
    if profile == "student_mistral":
        base = (
            gold.quality_thresholds.model_copy()
            if gold.quality_thresholds
            else Layer1QualityThresholds()
        )
        merged = base.model_dump()
        merged.update(STUDENT_MISTRAL_LAYER1_THRESHOLDS.model_dump())
        return gold.model_copy(
            update={"quality_thresholds": Layer1QualityThresholds.model_validate(merged)}
        )
    raise ValueError(f"unknown threshold profile: {profile!r}")
