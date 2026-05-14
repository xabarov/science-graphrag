"""``concept_topic_v2`` extractor: B re-labels each frozen concept as present/absent.

Pack layout:

    tests/fixtures/benchmarks/concept_topic/concepts_frozen_v1.json   (frozen 25 concepts)
    tests/fixtures/benchmarks/concept_topic/corpus_<slug>_v2/gold.json
    tests/fixtures/benchmarks/layer1/<slug>/article.md                (extractor input)

The gold lists `concepts_present` and `concepts_absent` per article. Extractor B
re-labels every frozen ``concept_id`` against the same ``article.md`` and the
matcher diffs the label sets by ``concept_id`` (no embedding scoring is needed —
the output space is closed at 25 ids). Useful failures we surface:

* **flips** — concept that A marked ``present`` but B marked ``absent`` (or vice versa);
* **missing_in_b** — A labelled it (either side), B did not include it;
* **extra_in_b** — B labelled it, A did not (e.g. A only covered a subset of frozen list).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from scripts.dual_validate.consistency_report import (
    ConsistencyReport,
    ExtractorInfo,
)
from scripts.dual_validate.extractors.base import (
    ExtractorBase,
    ExtractorRunOutput,
)
from scripts.dual_validate.llm_client import LLMCallSpec
from scripts.dual_validate.matcher import EmbeddingScorerProtocol

CONCEPT_TOPIC_SYSTEM_PROMPT = (
    "You are an independent extractor. For each given concept, decide whether the "
    "research article supports it as PRESENT (uses / introduces it) or ABSENT "
    "(does not use it / explicitly avoids it). Be conservative: if the article does "
    "not mention the concept by any alias and you cannot point to a verbatim quote, "
    "label it ABSENT with a short rationale. Always answer with a JSON object."
)

CONCEPT_TOPIC_USER_PROMPT_TEMPLATE = """Article and frozen concept list below.

For EACH concept in the frozen list (do not skip any), produce one entry:
- ``status``: "present" if the article uses / introduces the concept (must support with a verbatim ``evidence_quote`` <= 200 chars copied from the article), or "absent" with a short ``rationale`` (one sentence).
- Use the canonical ``concept_id`` exactly as given.
- Never invent ``concept_id`` outside the frozen list.

Output strictly this JSON object — no prose, no markdown:
{{
  "labels": [
    {{
      "concept_id": "<one of the frozen ids>",
      "status": "present" | "absent",
      "evidence_quote": "<verbatim, <=200 chars; required when status=present, omit/empty otherwise>",
      "rationale": "<one sentence; required when status=absent, omit/empty otherwise>"
    }}
  ]
}}

FROZEN_CONCEPTS (canonical_name + aliases per id):
{frozen_concepts}

ARTICLE:
=====
{article}
=====
"""

_VALID_STATUS = {"present", "absent"}


class ConceptLabelModel(BaseModel):
    concept_id: str = Field(min_length=1)
    status: str
    evidence_quote: str = Field(default="")
    rationale: str = Field(default="")


class ConceptTopicResponseModel(BaseModel):
    labels: list[ConceptLabelModel]


class ConceptTopicV2Extractor(ExtractorBase):
    """Independent LLM extractor for ``concept_topic/corpus_*_v2`` packs."""

    layer_name = "concept_topic_v2"
    response_model = ConceptTopicResponseModel

    def discover_packs(self, fixtures_root: Path) -> list[Path]:
        base = fixtures_root / "concept_topic"
        return sorted(d for d in base.glob("corpus_*_v2") if (d / "gold.json").exists())

    def _load_frozen_concepts(self, pack_dir: Path) -> list[dict]:
        frozen_path = pack_dir.parent / "concepts_frozen_v1.json"
        data = json.loads(frozen_path.read_text(encoding="utf-8"))
        return list(data.get("concepts", []))

    def _resolve_article(self, pack_dir: Path) -> Path:
        gold = json.loads((pack_dir / "gold.json").read_text(encoding="utf-8"))
        slug = gold.get("source_layer1_fixture") or gold.get("corpus_work_id")
        if not slug:
            raise ValueError(
                f"{pack_dir.name}: gold.json missing corpus_work_id/source_layer1_fixture"
            )
        article = pack_dir.parent.parent / "layer1" / slug / "article.md"
        if not article.exists():
            raise FileNotFoundError(f"{pack_dir.name}: article not found at {article}")
        return article

    def build_call_spec(self, pack_dir: Path, *, model: str, base_url: str) -> LLMCallSpec:
        frozen = self._load_frozen_concepts(pack_dir)
        article = self._resolve_article(pack_dir).read_text(encoding="utf-8")
        article = re.sub(r"\n{3,}", "\n\n", article)[:55000]
        frozen_text = "\n".join(
            f"- {c['concept_id']}: {c.get('canonical_name','')} (aliases: "
            f"{', '.join(c.get('aliases', [])) or 'none'})"
            for c in frozen
        )
        user = CONCEPT_TOPIC_USER_PROMPT_TEMPLATE.format(
            frozen_concepts=frozen_text,
            article=article,
        )
        return LLMCallSpec(
            model=model,
            base_url=base_url,
            system_prompt=CONCEPT_TOPIC_SYSTEM_PROMPT,
            user_prompt=user,
            temperature=0.1,
            max_tokens=4096,
            response_format="json_object",
        )

    def parse_response(self, raw_response: str) -> list[dict]:
        obj = self._safe_parse(raw_response)
        labels_raw = obj.get("labels") if isinstance(obj, dict) else obj
        if not isinstance(labels_raw, list):
            raise ValueError("extractor B response: missing/invalid 'labels' list")
        cleaned: list[dict] = []
        seen: set[str] = set()
        for entry in labels_raw:
            if not isinstance(entry, dict):
                continue
            cid = (entry.get("concept_id") or "").strip()
            status = (entry.get("status") or "").strip().lower()
            if not cid or status not in _VALID_STATUS:
                continue
            if cid in seen:
                continue
            seen.add(cid)
            cleaned.append(
                {
                    "concept_id": cid,
                    "status": status,
                    "evidence_quote": (entry.get("evidence_quote") or "").strip()[:300],
                    "rationale": (entry.get("rationale") or "").strip()[:400],
                }
            )
        return cleaned

    @staticmethod
    def _gold_labels(gold_a: dict) -> dict[str, str]:
        out: dict[str, str] = {}
        for c in gold_a.get("concepts_present", []):
            cid = c.get("concept_id")
            if cid:
                out[cid] = "present"
        for c in gold_a.get("concepts_absent", []):
            cid = c.get("concept_id")
            if cid and cid not in out:
                out[cid] = "absent"
        return out

    @staticmethod
    def _classify_priority(
        *,
        flip_count: int,
        missing_in_b: int,
        a_total: int,
    ) -> tuple[str, str]:
        miss_ratio = (missing_in_b / a_total) if a_total else 0.0
        if flip_count >= 1 or miss_ratio >= 0.40:
            return (
                "high",
                f"flips={flip_count}, missing_in_b_ratio={miss_ratio:.2f} "
                "(gate: flips ≥ 1 OR missing_in_b_ratio ≥ 0.40)",
            )
        if missing_in_b >= 2:
            return (
                "medium",
                f"missing_in_b={missing_in_b} (gate: missing_in_b ≥ 2 with no flips)",
            )
        return (
            "low",
            f"flips=0, missing_in_b={missing_in_b} (no gate hit)",
        )

    def build_report(
        self,
        pack_dir: Path,
        *,
        run: ExtractorRunOutput | None,
        gold_a: dict,
        embedding_scorer: EmbeddingScorerProtocol | None = None,  # noqa: ARG002 — closed-set diff
    ) -> ConsistencyReport:
        a_labels = self._gold_labels(gold_a)
        b_labels: dict[str, dict] = {}
        if run is not None:
            for entry in run.structured_b:
                b_labels[entry["concept_id"]] = entry

        matched_pairs: list[dict[str, Any]] = []
        unmatched_a: list[dict[str, Any]] = []
        unmatched_b: list[dict[str, Any]] = []
        flip_count = 0
        agree_present = agree_absent = 0
        for cid, a_status in a_labels.items():
            b_entry = b_labels.get(cid)
            if b_entry is None:
                unmatched_a.append(
                    {
                        "concept_id": cid,
                        "a_status": a_status,
                        "comment": "labelled in human gold A but not produced by extractor B",
                    }
                )
                continue
            b_status = b_entry["status"]
            field_disagreements = (
                [{"field": "status", "a": a_status, "b": b_status}] if a_status != b_status else []
            )
            if field_disagreements:
                flip_count += 1
            elif a_status == "present":
                agree_present += 1
            else:
                agree_absent += 1
            matched_pairs.append(
                {
                    "concept_id": cid,
                    "a_status": a_status,
                    "b_status": b_status,
                    "match_score": 1.0,
                    "match_source": "concept_id_exact",
                    "field_disagreements": field_disagreements,
                    "b_evidence_quote": b_entry.get("evidence_quote", ""),
                    "b_rationale": b_entry.get("rationale", ""),
                }
            )

        for cid, b_entry in b_labels.items():
            if cid in a_labels:
                continue
            unmatched_b.append(
                {
                    "concept_id": cid,
                    "b_status": b_entry["status"],
                    "b_evidence_quote": b_entry.get("evidence_quote", ""),
                    "b_rationale": b_entry.get("rationale", ""),
                    "comment": "labelled by extractor B but absent from human gold A",
                }
            )

        priority, why = self._classify_priority(
            flip_count=flip_count,
            missing_in_b=len(unmatched_a),
            a_total=len(a_labels),
        )

        rel_pack, rel_gold = self._safe_relative_paths(pack_dir)

        a_info = ExtractorInfo(
            role="human_authored_existing_gold",
            source=str(rel_gold),
            count=len(a_labels),
        )
        b_info = self._extractor_b_info(
            run,
            role="llm_independent_extraction",
            source="article.md (re-labelled against frozen 25 concepts)",
            count=len(b_labels),
        )

        summary = self._summary_skeleton(
            a_total=len(a_labels),
            b_total=len(b_labels),
            matched_pairs=matched_pairs,
            unmatched_a=unmatched_a,
            unmatched_b=unmatched_b,
            field_agreements={
                "status": {
                    "agreed_present": agree_present,
                    "agreed_absent": agree_absent,
                    "flips": flip_count,
                }
            },
        )
        return ConsistencyReport(
            pack_id=f"concept_topic/{pack_dir.name}",
            pack_path=str(rel_pack),
            layer=self.layer_name,
            extractor_a=a_info,
            extractor_b=b_info,
            matched_pairs=matched_pairs,
            unmatched_a=unmatched_a,
            unmatched_b=unmatched_b,
            summary=summary,
            spot_check_priority=priority,
            spot_check_priority_rationale=why,
        )
