"""``hybrid_ablation_v2`` retrieval dual-validate extractor (B)."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from scripts.dual_validate.consistency_report import ConsistencyReport
from scripts.dual_validate.extractors.base import (
    ExtractorBase,
    ExtractorRunOutput,
)
from scripts.dual_validate.extractors.retrieval_v1_consistency_reports import (
    hybrid_ablation_v2_consistency_report,
)
from scripts.dual_validate.extractors.retrieval_v1_inventory import load_inventory
from scripts.dual_validate.extractors.retrieval_v1_pack_io import (
    discover_pack_directories,
    read_pack_gold_json,
)
from scripts.dual_validate.extractors.retrieval_v1_prompts import (
    HYBRID_ABLATION_SYSTEM,
    HYBRID_ABLATION_USER,
)
from scripts.dual_validate.extractors.retrieval_v1_ranking import (
    format_candidates as _format_candidates,
)
from scripts.dual_validate.extractors.retrieval_v1_schema import HybridAblationResponseModel
from scripts.dual_validate.llm_client import LLMCallSpec
from scripts.dual_validate.matcher import EmbeddingScorerProtocol

# Mirrors sibling extractors' ``build_report`` tail by design.
# pylint: disable=duplicate-code


class HybridAblationV2Extractor(ExtractorBase):
    """B classifies relevant vs irrelevant candidates for ``hybrid_ablation_v2`` packs."""

    layer_name = "hybrid_ablation_v2"
    fixtures_subdir: ClassVar[str] = "retrieval/hybrid_ablation_v2"
    response_model = HybridAblationResponseModel

    def discover_packs(self, fixtures_root: Path) -> list[Path]:
        return discover_pack_directories(fixtures_root, self.fixtures_subdir)

    def _gold(self, pack_dir: Path) -> dict:
        return read_pack_gold_json(pack_dir)

    def build_call_spec(self, pack_dir: Path, *, model: str, base_url: str) -> LLMCallSpec:
        gold = self._gold(pack_dir)
        question = (pack_dir / "question.txt").read_text(encoding="utf-8").strip()
        candidates = sorted(
            set(gold.get("relevant_corpus_work_ids", []))
            | set(gold.get("irrelevant_corpus_work_ids", []))
        )
        inv = load_inventory()
        block = _format_candidates(candidates, inv)
        return LLMCallSpec(
            model=model,
            base_url=base_url,
            system_prompt=HYBRID_ABLATION_SYSTEM,
            user_prompt=HYBRID_ABLATION_USER.format(question=question, candidates_block=block),
            temperature=0.1,
            max_tokens=1024,
            response_format="json_object",
        )

    def parse_response(self, raw_response: str) -> list[dict]:
        obj = self._safe_parse(raw_response, layer_label="hybrid_ablation_v2")
        if not isinstance(obj, dict):
            raise ValueError("extractor B response: top-level must be a JSON object")
        return [
            {
                "relevant": [
                    str(x)
                    for x in (obj.get("relevant_corpus_work_ids") or [])
                    if isinstance(x, str)
                ],
                "irrelevant": [
                    str(x)
                    for x in (obj.get("irrelevant_corpus_work_ids") or [])
                    if isinstance(x, str)
                ],
                "rationale": str(obj.get("rationale") or "").strip()[:400],
            }
        ]

    def build_report(
        self,
        pack_dir: Path,
        *,
        run: ExtractorRunOutput | None,
        gold_a: dict,
        embedding_scorer: EmbeddingScorerProtocol | None = None,  # noqa: ARG002
    ) -> ConsistencyReport:
        return hybrid_ablation_v2_consistency_report(
            pack_dir,
            run=run,
            gold_a=gold_a,
            layer_name=self.layer_name,
            embedding_scorer=embedding_scorer,
        )
