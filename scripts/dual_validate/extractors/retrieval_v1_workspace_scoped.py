"""``workspace_scoped_live`` retrieval dual-validate extractor (B)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

from scripts.dual_validate.consistency_report import ConsistencyReport
from scripts.dual_validate.extractors.base import (
    ExtractorBase,
    ExtractorRunOutput,
)
from scripts.dual_validate.extractors.retrieval_v1_consistency_reports import (
    workspace_scoped_live_consistency_report,
)
from scripts.dual_validate.extractors.retrieval_v1_inventory import (
    WORKSPACES_PATH,
    load_inventory,
)
from scripts.dual_validate.extractors.retrieval_v1_pack_io import (
    discover_pack_directories,
    read_pack_gold_json,
)
from scripts.dual_validate.extractors.retrieval_v1_prompts import (
    WORKSPACE_SCOPED_SYSTEM,
    WORKSPACE_SCOPED_USER,
)
from scripts.dual_validate.extractors.retrieval_v1_ranking import (
    format_candidates as _format_candidates,
)
from scripts.dual_validate.extractors.retrieval_v1_schema import WorkspaceScopedResponseModel
from scripts.dual_validate.llm_client import LLMCallSpec
from scripts.dual_validate.matcher import EmbeddingScorerProtocol

# Mirrors sibling extractors' ``build_report`` tail by design.
# pylint: disable=duplicate-code


class WorkspaceScopedLiveExtractor(ExtractorBase):
    """B re-derives expected corpus work ids for ``workspace_scoped_live`` packs."""

    layer_name = "workspace_scoped_live"
    fixtures_subdir: ClassVar[str] = "retrieval/workspace_scoped_live"
    response_model = WorkspaceScopedResponseModel

    def discover_packs(self, fixtures_root: Path) -> list[Path]:
        return discover_pack_directories(fixtures_root, self.fixtures_subdir)

    def _gold(self, pack_dir: Path) -> dict:
        return read_pack_gold_json(pack_dir)

    def _question(self, pack_dir: Path) -> str:
        return (pack_dir / "question.txt").read_text(encoding="utf-8").strip()

    def _workspace_papers(self, ws_id: str) -> list[str]:
        ws = json.loads(WORKSPACES_PATH.read_text(encoding="utf-8"))["workspaces"]
        spec = ws.get(ws_id) or {}
        ids = spec.get("corpus_work_ids", [])
        if ids == "*":
            return sorted(load_inventory().keys())
        return list(ids)

    def build_call_spec(self, pack_dir: Path, *, model: str, base_url: str) -> LLMCallSpec:
        gold = self._gold(pack_dir)
        question = self._question(pack_dir)
        ws_id = gold["workspace_id"]
        workspace_ids = self._workspace_papers(ws_id)
        forbidden_ids = list(gold.get("forbidden_corpus_work_ids", []))
        inv = load_inventory()
        ws_block = _format_candidates(workspace_ids, inv)
        forbidden_block = _format_candidates(forbidden_ids, inv) or "  (none)"
        user = WORKSPACE_SCOPED_USER.format(
            ws_name=ws_id,
            workspace_block=ws_block,
            forbidden_block=forbidden_block,
            question=question,
        )
        return LLMCallSpec(
            model=model,
            base_url=base_url,
            system_prompt=WORKSPACE_SCOPED_SYSTEM,
            user_prompt=user,
            temperature=0.1,
            max_tokens=1024,
            response_format="json_object",
        )

    def parse_response(self, raw_response: str) -> list[dict]:
        obj = self._safe_parse(raw_response, layer_label="workspace_scoped_live")
        if not isinstance(obj, dict):
            raise ValueError("extractor B response: top-level must be a JSON object")
        return [
            {
                "expected_corpus_work_ids": [
                    str(x)
                    for x in (obj.get("expected_corpus_work_ids") or [])
                    if isinstance(x, str)
                ],
                "would_violate_workspace_with": [
                    str(x)
                    for x in (obj.get("would_violate_workspace_with") or [])
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
        embedding_scorer: EmbeddingScorerProtocol | None = None,  # noqa: ARG002 — set diff
    ) -> ConsistencyReport:
        return workspace_scoped_live_consistency_report(
            pack_dir,
            run=run,
            gold_a=gold_a,
            layer_name=self.layer_name,
            embedding_scorer=embedding_scorer,
        )
