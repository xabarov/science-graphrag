"""Per-layer extractors for dual-validate. One module per Corpus Gold Pack v1 layer."""

from scripts.dual_validate.extractors.base import ExtractorBase, ExtractorRunOutput
from scripts.dual_validate.extractors.claims_v2 import ClaimsV2Extractor

__all__ = ["ExtractorBase", "ExtractorRunOutput", "ClaimsV2Extractor"]
