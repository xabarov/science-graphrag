"""``retrieval/*`` extractors: B re-derives expected work ids from a question.

Three layers share the same shape:

* ``workspace_scoped_live`` — B sees question + workspace papers + the rest of
  the corpus, predicts which corpus_work_ids are relevant inside the workspace
  and which (if any) of the explicitly forbidden ids it would mistakenly cite.
* ``hybrid_ablation_v2`` — B classifies a candidate set (``relevant +
  irrelevant`` from gold) into the two buckets without seeing gold labels.
* ``multihop_v2`` — B is told the path kind (``ordered_chain`` or
  ``unordered_set``) and the question, then returns either the chain or the
  expected node ids/canonical names.

Output space is closed (``corpus_work_id``s / canonical author names supplied
in the inventory), so embedding cascade is not used. The matcher computes
set-overlap precision / recall / Jaccard plus, for ``ordered_chain``,
Kendall-style order correctness.

Implementation is split across ``retrieval_v1_*`` modules; this file re-exports
the public extractor classes for stable import paths.
"""

from __future__ import annotations

from scripts.dual_validate.extractors.retrieval_v1_hybrid_ablation import HybridAblationV2Extractor
from scripts.dual_validate.extractors.retrieval_v1_multihop import MultihopV2Extractor
from scripts.dual_validate.extractors.retrieval_v1_workspace_scoped import (
    WorkspaceScopedLiveExtractor,
)

__all__ = [
    "HybridAblationV2Extractor",
    "MultihopV2Extractor",
    "WorkspaceScopedLiveExtractor",
]
