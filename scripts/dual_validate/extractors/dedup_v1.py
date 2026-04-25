"""``dedup/<entity_type>_v1`` extractors: B re-clusters surface forms.

Pack layout (one per entity type):

    tests/fixtures/benchmarks/dedup/<entity_type>_v1/gold.json
    tests/fixtures/benchmarks/dedup/<entity_type>_v1/README.md

Each gold pack lists 19-25 surface form records (same entity appears in multiple
forms across the corpus) with positive ``clusters`` (must merge) and
``negative_pairs`` (must NOT merge). Extractor B receives the same record list
and is asked to re-derive the clustering. The matcher diffs:

* **clusters** — pair-counting precision / recall + Adjusted Rand Index;
* **negative_pairs** — set agreement on must-not-merge constraints.

Embedding cascade is not applicable: comparison is over closed sets of
``entity_id``s assigned by both extractors. The output space is defined entirely
by the input record ids.
"""

from __future__ import annotations

import json
from itertools import combinations
from math import comb
from pathlib import Path
from typing import Any, ClassVar

from scripts.dual_validate.consistency_report import (
    ConsistencyReport,
    ExtractorInfo,
)
from scripts.dual_validate.extractors.base import (
    ExtractorBase,
    ExtractorRunOutput,
    parse_json_object_lenient,
)
from scripts.dual_validate.llm_client import LLMCallSpec
from scripts.dual_validate.matcher import EmbeddingScorerProtocol

_DEDUP_SYSTEM_PROMPT = (
    "You are an independent entity-resolution reviewer. Given a list of surface "
    "form records, group them into clusters that refer to the same real-world "
    "entity. Also flag pairs that look superficially similar but MUST NOT merge "
    "(e.g. different first names that share a surname). Always answer with a "
    "JSON object."
)

_DEDUP_USER_PROMPT_TEMPLATE = """Resolve the {entity_type} records below.

Rules:
- Two records belong to the SAME cluster only when context_attributes (years, work ids, affiliations, task) corroborate the surface match.
- Singleton entities (no other record matches) MUST still appear as their own cluster.
- For pairs that look identical on the surface but the context shows they are different, list them under negative_pairs.
- Only reference entity_ids exactly as given; do not invent ids.
- Cluster_id / pair_id are free-form short slugs you choose.

Output strictly this JSON object — no prose, no markdown:
{{
  "clusters": [
    {{"cluster_id": "<short slug>", "entity_ids": ["<id>", "<id>", ...], "rationale": "<one sentence>"}}
  ],
  "negative_pairs": [
    {{"pair_id": "<short slug>", "entity_ids": ["<id>", "<id>"], "rationale": "<one sentence>"}}
  ]
}}

DOMAIN HINT: {domain_hint}

RECORDS:
{records_block}
"""


def _records_to_block(records: list[dict]) -> str:
    lines: list[str] = []
    for r in records:
        attrs = r.get("context_attributes") or {}
        attrs_inline = json.dumps(attrs, ensure_ascii=False)
        lines.append(
            f"  - entity_id: {r['entity_id']} | display_name: {r.get('display_name','')} "
            f"| surface_form: {r.get('surface_form','')} | context: {attrs_inline}"
        )
    return "\n".join(lines)


def _validate_clusters(
    clusters_raw: list[dict],
    valid_ids: set[str],
) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for c in clusters_raw or []:
        if not isinstance(c, dict):
            continue
        eids_raw = c.get("entity_ids") or []
        eids = [str(eid).strip() for eid in eids_raw if isinstance(eid, str)]
        eids = [eid for eid in eids if eid in valid_ids and eid not in seen]
        if not eids:
            continue
        seen.update(eids)
        out.append(
            {
                "cluster_id": (str(c.get("cluster_id") or "")).strip()[:120]
                or f"cluster_{len(out) + 1}",
                "entity_ids": sorted(eids),
                "rationale": (str(c.get("rationale") or "")).strip()[:400],
            }
        )
    # Cover ids that B did not place anywhere — promote to singletons so the
    # diff against A is meaningful (B did not "drop" them, just declined to merge).
    missing = sorted(valid_ids - seen)
    for eid in missing:
        out.append(
            {
                "cluster_id": f"singleton_{eid}",
                "entity_ids": [eid],
                "rationale": "implicit singleton (B did not assign this record to any cluster)",
            }
        )
    return out


def _validate_negative_pairs(
    pairs_raw: list[dict],
    valid_ids: set[str],
) -> list[dict]:
    out: list[dict] = []
    seen: set[frozenset] = set()
    for p in pairs_raw or []:
        if not isinstance(p, dict):
            continue
        eids_raw = p.get("entity_ids") or []
        eids = [str(eid).strip() for eid in eids_raw if isinstance(eid, str)]
        eids = [eid for eid in eids if eid in valid_ids]
        if len(eids) != 2:
            continue
        key = frozenset(eids)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "pair_id": (str(p.get("pair_id") or "")).strip()[:120] or f"neg_{len(out) + 1}",
                "entity_ids": sorted(eids),
                "rationale": (str(p.get("rationale") or "")).strip()[:400],
            }
        )
    return out


def _cluster_label_map(clusters: list[dict]) -> dict[str, str]:
    out: dict[str, str] = {}
    for c in clusters:
        label = c["cluster_id"]
        for eid in c["entity_ids"]:
            out[eid] = label
    return out


def _pair_counting_metrics(
    a_labels: dict[str, str],
    b_labels: dict[str, str],
) -> dict[str, float]:
    """Pair-counting precision/recall + Adjusted Rand Index over shared ids."""

    common = sorted(set(a_labels) & set(b_labels))
    if len(common) < 2:
        return {
            "shared_ids": len(common),
            "pair_precision": 0.0,
            "pair_recall": 0.0,
            "pair_f1": 0.0,
            "adjusted_rand_index": 0.0,
        }
    pairs_a = {frozenset({i, j}) for i, j in combinations(common, 2) if a_labels[i] == a_labels[j]}
    pairs_b = {frozenset({i, j}) for i, j in combinations(common, 2) if b_labels[i] == b_labels[j]}
    tp = len(pairs_a & pairs_b)
    precision = tp / len(pairs_b) if pairs_b else 0.0
    recall = tp / len(pairs_a) if pairs_a else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    # ARI via pair-counting (Hubert–Arabie formulation).
    a_lbls = sorted({a_labels[i] for i in common})
    b_lbls = sorted({b_labels[i] for i in common})
    contingency: dict[tuple[str, str], int] = {}
    for i in common:
        contingency[(a_labels[i], b_labels[i])] = contingency.get((a_labels[i], b_labels[i]), 0) + 1
    n = len(common)
    sum_choose_nij = sum(comb(v, 2) for v in contingency.values())
    a_marginals = {al: sum(contingency.get((al, bl), 0) for bl in b_lbls) for al in a_lbls}
    b_marginals = {bl: sum(contingency.get((al, bl), 0) for al in a_lbls) for bl in b_lbls}
    sum_choose_a = sum(comb(v, 2) for v in a_marginals.values())
    sum_choose_b = sum(comb(v, 2) for v in b_marginals.values())
    expected = sum_choose_a * sum_choose_b / comb(n, 2) if comb(n, 2) else 0.0
    max_idx = (sum_choose_a + sum_choose_b) / 2.0
    denom = max_idx - expected
    ari = (sum_choose_nij - expected) / denom if denom else 1.0
    return {
        "shared_ids": len(common),
        "pair_precision": round(precision, 3),
        "pair_recall": round(recall, 3),
        "pair_f1": round(f1, 3),
        "adjusted_rand_index": round(ari, 3),
    }


class DedupExtractorBase(ExtractorBase):
    """Common scaffolding for all 5 ``dedup/<entity_type>_v1`` extractors.

    Concrete subclasses set ``layer_name``, ``entity_type``, and ``domain_hint``.
    Each gold pack contains a single ``records`` list, ``clusters`` (positive),
    and ``negative_pairs`` (negative). One LLM call per pack covers the entire
    layer — ~5 calls total across all dedup types, kept cheap by design.
    """

    entity_type: ClassVar[str] = "abstract"
    domain_hint: ClassVar[str] = ""
    fixtures_subdir: ClassVar[str] = "dedup"

    def discover_packs(self, fixtures_root: Path) -> list[Path]:
        pack = fixtures_root / self.fixtures_subdir / f"{self.entity_type}s_v1"
        return [pack] if (pack / "gold.json").exists() else []

    def _gold(self, pack_dir: Path) -> dict:
        return json.loads((pack_dir / "gold.json").read_text(encoding="utf-8"))

    def build_call_spec(self, pack_dir: Path, *, model: str, base_url: str) -> LLMCallSpec:
        gold = self._gold(pack_dir)
        records = list(gold.get("records", []))
        block = _records_to_block(records)
        user = _DEDUP_USER_PROMPT_TEMPLATE.format(
            entity_type=self.entity_type,
            domain_hint=self.domain_hint,
            records_block=block,
        )
        return LLMCallSpec(
            model=model,
            base_url=base_url,
            system_prompt=_DEDUP_SYSTEM_PROMPT,
            user_prompt=user,
            temperature=0.1,
            max_tokens=4096,
            response_format="json_object",
        )

    def parse_response(self, raw_response: str) -> list[dict]:
        try:
            obj = parse_json_object_lenient(raw_response)
        except ValueError as exc:
            raise ValueError(f"extractor B (dedup/{self.entity_type}_v1): {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError("extractor B response: top-level must be a JSON object")
        return [
            {
                "clusters": list(obj.get("clusters") or []),
                "negative_pairs": list(obj.get("negative_pairs") or []),
            }
        ]

    @staticmethod
    def _classify_priority(metrics: dict[str, float], neg_diff_count: int) -> tuple[str, str]:
        ari = metrics["adjusted_rand_index"]
        f1 = metrics["pair_f1"]
        if ari >= 0.95 and f1 >= 0.95 and neg_diff_count == 0:
            return ("low", f"ARI={ari:.2f}, pair_f1={f1:.2f}, neg_diffs=0")
        if ari >= 0.80 and f1 >= 0.80:
            return (
                "medium",
                f"ARI={ari:.2f}, pair_f1={f1:.2f}, neg_diffs={neg_diff_count}",
            )
        return (
            "high",
            f"ARI={ari:.2f}, pair_f1={f1:.2f}, neg_diffs={neg_diff_count} "
            "(gate: ARI<0.80 OR pair_f1<0.80)",
        )

    def build_report(
        self,
        pack_dir: Path,
        *,
        run: ExtractorRunOutput | None,
        gold_a: dict,
        embedding_scorer: EmbeddingScorerProtocol | None = None,  # noqa: ARG002 — closed-set diff
    ) -> ConsistencyReport:
        records = list(gold_a.get("records", []))
        valid_ids = {r["entity_id"] for r in records}
        a_clusters = _validate_clusters(list(gold_a.get("clusters", [])), valid_ids)
        a_neg_pairs = _validate_negative_pairs(list(gold_a.get("negative_pairs", [])), valid_ids)
        b_clusters: list[dict] = []
        b_neg_pairs: list[dict] = []
        if run is not None and run.structured_b:
            payload = run.structured_b[0]
            b_clusters = _validate_clusters(payload["clusters"], valid_ids)
            b_neg_pairs = _validate_negative_pairs(payload["negative_pairs"], valid_ids)

        a_labels = _cluster_label_map(a_clusters)
        b_labels = _cluster_label_map(b_clusters)
        metrics = (
            _pair_counting_metrics(a_labels, b_labels)
            if b_labels
            else {
                "shared_ids": 0,
                "pair_precision": 0.0,
                "pair_recall": 0.0,
                "pair_f1": 0.0,
                "adjusted_rand_index": 0.0,
            }
        )

        a_neg_set = {frozenset(p["entity_ids"]) for p in a_neg_pairs}
        b_neg_set = {frozenset(p["entity_ids"]) for p in b_neg_pairs}
        neg_agreed = a_neg_set & b_neg_set
        neg_only_a = a_neg_set - b_neg_set
        neg_only_b = b_neg_set - a_neg_set

        # Pair-level diff: per-cluster show entities A grouped that B split, and vice versa.
        matched_pairs: list[dict[str, Any]] = []
        for c in a_clusters:
            if len(c["entity_ids"]) < 2:
                continue
            b_groups: dict[str, list[str]] = {}
            for eid in c["entity_ids"]:
                lbl = b_labels.get(eid, f"<missing:{eid}>")
                b_groups.setdefault(lbl, []).append(eid)
            agreement_score = max(len(g) for g in b_groups.values()) / len(c["entity_ids"])
            matched_pairs.append(
                {
                    "a_cluster_id": c["cluster_id"],
                    "a_entity_ids": c["entity_ids"],
                    "b_cluster_partition": {k: sorted(v) for k, v in b_groups.items()},
                    "match_score": round(agreement_score, 3),
                    "match_source": "pair_counting",
                    "field_disagreements": (
                        []
                        if len(b_groups) == 1
                        else [
                            {
                                "field": "cluster_membership",
                                "a": "single_cluster",
                                "b": f"split_into_{len(b_groups)}",
                            }
                        ]
                    ),
                }
            )

        unmatched_a: list[dict[str, Any]] = []
        for p in sorted(neg_only_a, key=sorted):
            unmatched_a.append(
                {
                    "kind": "negative_pair_missing_in_b",
                    "entity_ids": sorted(p),
                    "comment": "must-not-merge constraint declared by gold A but not flagged by B",
                }
            )
        unmatched_b: list[dict[str, Any]] = []
        for p in sorted(neg_only_b, key=sorted):
            unmatched_b.append(
                {
                    "kind": "negative_pair_extra_in_b",
                    "entity_ids": sorted(p),
                    "comment": "B flagged this as must-not-merge but gold A did not",
                }
            )
        for c in b_clusters:
            if len(c["entity_ids"]) < 2:
                continue
            members_in_a = {a_labels.get(eid) for eid in c["entity_ids"]}
            members_in_a.discard(None)
            if len(members_in_a) > 1:
                unmatched_b.append(
                    {
                        "kind": "merge_extra_in_b",
                        "b_cluster_id": c["cluster_id"],
                        "b_entity_ids": c["entity_ids"],
                        "comment": (
                            f"B merged records that gold A keeps in different clusters: {sorted(members_in_a)}"
                        ),
                    }
                )

        priority, why = self._classify_priority(
            metrics,
            neg_diff_count=len(neg_only_a) + len(neg_only_b),
        )

        gold_path = (pack_dir / "gold.json").resolve()
        try:
            rel_pack = pack_dir.resolve().relative_to(Path.cwd())
            rel_gold = gold_path.relative_to(Path.cwd())
        except ValueError:
            rel_pack = pack_dir
            rel_gold = gold_path

        a_info = ExtractorInfo(
            role="human_authored_existing_gold",
            source=str(rel_gold),
            count=len(a_clusters),
        )
        if run is None:
            b_info = ExtractorInfo(
                role="llm_independent_extraction_dry_run",
                source="dry-run (no LLM call)",
                count=0,
            )
        else:
            b_info = ExtractorInfo(
                role="llm_independent_extraction",
                source=f"records list ({len(records)} surface forms re-clustered)",
                model=run.call_spec.model,
                base_url=run.call_spec.base_url,
                prompt_hash=run.prompt_hash,
                count=len(b_clusters),
                usage_tokens=run.usage_tokens,
                latency_ms=run.latency_ms,
            )

        summary = {
            "a_total": len(a_clusters),
            "b_total": len(b_clusters),
            "matched": len(matched_pairs),
            "matched_lexical": len(matched_pairs),
            "matched_embedding": 0,
            "unmatched_a": len(unmatched_a),
            "unmatched_b": len(unmatched_b),
            "metrics": metrics,
            "negative_pairs": {
                "agreed": len(neg_agreed),
                "only_in_a": len(neg_only_a),
                "only_in_b": len(neg_only_b),
            },
        }
        return ConsistencyReport(
            pack_id=f"dedup/{self.entity_type}s_v1",
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


class DedupAuthorsV1Extractor(DedupExtractorBase):
    layer_name = "dedup_authors_v1"
    entity_type = "author"
    domain_hint = (
        "Object-detection paper authors (2014-2024). Initial-only forms (e.g. 'J. Redmon') "
        "may collapse to a full name only when affiliations + co-publishing patterns match. "
        "Common-surname collisions (Zhang, Lin, He) require disambiguation by first name."
    )


class DedupInstitutionsV1Extractor(DedupExtractorBase):
    layer_name = "dedup_institutions_v1"
    entity_type = "institution"
    domain_hint = (
        "Universities + industrial research labs that publish object detection. "
        "Watch for re-brandings (Facebook AI Research → Meta AI), abbreviations "
        "(MSR / MSRA / Microsoft Research), and unrelated namesakes (e.g. 'Microsoft Research Asia' vs 'Microsoft Research Cambridge')."
    )


class DedupVenuesV1Extractor(DedupExtractorBase):
    layer_name = "dedup_venues_v1"
    entity_type = "venue"
    domain_hint = (
        "Computer vision venues: CVPR / ICCV / ECCV / NeurIPS / ICLR + arXiv preprint. "
        "arXiv preprint is NOT the same venue as a later conference publication of the same paper. "
        "Year-stamped variants (CVPR 2017 vs CVPR 2018) belong to the same venue cluster."
    )


class DedupMethodsV1Extractor(DedupExtractorBase):
    layer_name = "dedup_methods_v1"
    entity_type = "method"
    domain_hint = (
        "Object detection methods. CRITICAL: superficially similar names are "
        "DIFFERENT methods (R-CNN ≠ Fast R-CNN ≠ Faster R-CNN ≠ Mask R-CNN; "
        "DETR ≠ Deformable DETR ≠ DN-DETR ≠ DINO). Only typographic/expansion variants "
        "of the SAME method (e.g. 'R-CNN' vs 'RCNN' vs 'Region-based Convolutional Neural Network') merge."
    )


class DedupDatasetsV1Extractor(DedupExtractorBase):
    layer_name = "dedup_datasets_v1"
    entity_type = "dataset"
    domain_hint = (
        "Object detection datasets: PASCAL VOC, MS COCO, ImageNet, Open Images, etc. "
        "Versioned variants (COCO 2014 vs COCO 2017) usually belong to the same dataset cluster. "
        "Sub-splits (val vs test-dev) are part of the parent dataset cluster, but separate datasets "
        "(e.g. ImageNet vs ImageNet-DET) are distinct."
    )
