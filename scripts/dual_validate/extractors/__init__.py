"""Per-layer extractors for dual-validate. One module per Corpus Gold Pack v1 layer."""

from scripts.dual_validate.extractors.agent_tools_live import AgentToolsLiveExtractor
from scripts.dual_validate.extractors.base import ExtractorBase, ExtractorRunOutput
from scripts.dual_validate.extractors.claims_v2 import ClaimsV2Extractor
from scripts.dual_validate.extractors.concept_topic_v2 import ConceptTopicV2Extractor
from scripts.dual_validate.extractors.contradictions_v1 import ContradictionsV1Extractor
from scripts.dual_validate.extractors.dedup_v1 import (
    DedupAuthorsV1Extractor,
    DedupDatasetsV1Extractor,
    DedupExtractorBase,
    DedupInstitutionsV1Extractor,
    DedupMethodsV1Extractor,
    DedupVenuesV1Extractor,
)
from scripts.dual_validate.extractors.idea_assist_live import IdeaAssistLiveExtractor
from scripts.dual_validate.extractors.retrieval_v1 import (
    HybridAblationV2Extractor,
    MultihopV2Extractor,
    WorkspaceScopedLiveExtractor,
)

__all__ = [
    "ExtractorBase",
    "ExtractorRunOutput",
    "AgentToolsLiveExtractor",
    "ClaimsV2Extractor",
    "ConceptTopicV2Extractor",
    "ContradictionsV1Extractor",
    "DedupExtractorBase",
    "DedupAuthorsV1Extractor",
    "DedupInstitutionsV1Extractor",
    "DedupVenuesV1Extractor",
    "DedupMethodsV1Extractor",
    "DedupDatasetsV1Extractor",
    "IdeaAssistLiveExtractor",
    "WorkspaceScopedLiveExtractor",
    "HybridAblationV2Extractor",
    "MultihopV2Extractor",
]
