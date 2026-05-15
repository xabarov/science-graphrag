"""``multihop_v2`` retrieval dual-validate extractor (B)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from scripts.dual_validate.consistency_report import ConsistencyReport
from scripts.dual_validate.extractors.base import (
    ExtractorBase,
    ExtractorRunOutput,
)
from scripts.dual_validate.extractors.retrieval_v1_consistency_reports import (
    multihop_v2_consistency_report,
)
from scripts.dual_validate.extractors.retrieval_v1_inventory import load_inventory
from scripts.dual_validate.extractors.retrieval_v1_pack_io import (
    discover_pack_directories,
    read_pack_gold_json,
)
from scripts.dual_validate.extractors.retrieval_v1_prompts import (
    MULTIHOP_SYSTEM,
    MULTIHOP_USER_CHAIN,
    MULTIHOP_USER_SET,
)
from scripts.dual_validate.extractors.retrieval_v1_ranking import (
    format_candidates as _format_candidates,
)
from scripts.dual_validate.extractors.retrieval_v1_schema import MultihopResponseModel
from scripts.dual_validate.llm_client import LLMCallSpec
from scripts.dual_validate.matcher import EmbeddingScorerProtocol

# Mirrors sibling extractors' ``build_report`` tail by design.
# pylint: disable=duplicate-code


class MultihopV2Extractor(ExtractorBase):
    """B predicts chain or node set for ``multihop_v2`` packs."""

    layer_name = "multihop_v2"
    fixtures_subdir: ClassVar[str] = "retrieval/multihop_v2"
    response_model = MultihopResponseModel

    def discover_packs(self, fixtures_root: Path) -> list[Path]:
        return discover_pack_directories(fixtures_root, self.fixtures_subdir)

    def _gold(self, pack_dir: Path) -> dict:
        return read_pack_gold_json(pack_dir)

    def _candidate_ids(self, gold: dict, inventory: dict[str, Any]) -> list[str]:
        # Provide a generous inventory so B has to filter, not guess.
        if gold.get("expected_path_kind") == "ordered_chain":
            return list(gold.get("expected_chain_corpus_work_ids", []))
        # Set node case: include relevant + a small distractor pool from inventory.
        return sorted(inventory.keys())

    def build_call_spec(self, pack_dir: Path, *, model: str, base_url: str) -> LLMCallSpec:
        gold = self._gold(pack_dir)
        question = (pack_dir / "question.txt").read_text(encoding="utf-8").strip()
        inv = load_inventory()
        candidates = self._candidate_ids(gold, inv)
        block = _format_candidates(candidates, inv)
        if gold.get("expected_path_kind") == "ordered_chain":
            user = MULTIHOP_USER_CHAIN.format(question=question, candidates_block=block)
        else:
            user = MULTIHOP_USER_SET.format(
                question=question,
                node_kind=gold.get("expected_node_kind", "unspecified"),
                candidates_block=block,
            )
        return LLMCallSpec(
            model=model,
            base_url=base_url,
            system_prompt=MULTIHOP_SYSTEM,
            user_prompt=user,
            temperature=0.1,
            max_tokens=1024,
            response_format="json_object",
        )

    def parse_response(self, raw_response: str) -> list[dict]:
        obj = self._safe_parse(raw_response, layer_label="multihop_v2")
        if not isinstance(obj, dict):
            raise ValueError("extractor B response: top-level must be a JSON object")
        return [
            {
                "expected_chain_corpus_work_ids": [
                    str(x)
                    for x in (obj.get("expected_chain_corpus_work_ids") or [])
                    if isinstance(x, str)
                ],
                "expected_node_canonical_names": [
                    str(x)
                    for x in (obj.get("expected_node_canonical_names") or [])
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
        embedding_scorer: EmbeddingScorerProtocol | None = None,  # noqa: ARG002 — set/order diff
    ) -> ConsistencyReport:
        return multihop_v2_consistency_report(
            pack_dir,
            run=run,
            gold_a=gold_a,
            layer_name=self.layer_name,
            embedding_scorer=embedding_scorer,
        )
