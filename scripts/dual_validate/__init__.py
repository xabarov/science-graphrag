"""Phase 6 — dual-LLM gold validation framework.

This package powers ``scripts/dual_extract_validate.py``: an independent extractor B
runs over each Corpus Gold Pack v1 layer and produces a ``consistency_report.json``
that highlights agreements / disagreements with the human-authored extractor A.

Layered structure:

- ``llm_client``       : OpenAI-compatible (OpenRouter) wrapper.
- ``consistency_report``: schema + IO helpers for ``consistency_report.json``.
- ``matcher``          : algorithmic A/B claim matching (Jaccard token overlap, greedy bipartite).
- ``extractors.base``  : abstract extractor interface (one impl per layer).
- ``extractors.claims_v2``: claims_v2 layer extractor (PoC).
"""
