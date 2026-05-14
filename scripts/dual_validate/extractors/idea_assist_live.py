"""``idea_assist_live`` extractor: B reviews the gold for adequacy, not for output.

Pack layout (one per case):

    tests/fixtures/benchmarks/idea_assist_v1/live_<NN>_<slug>/gold.json
    tests/fixtures/benchmarks/idea_assist_v1/live_<NN>_<slug>/scenario.json

Unlike claims/concepts/contradictions, the gold here does not enumerate
"facts to extract" — it specifies *gates* for what an idea-assist runner is
allowed to produce (supporting claim pool, forbidden substrings, RougeL ceiling
against evidence quotes, novelty requirement). Phase 6.D semantic matching does
not apply directly; instead extractor B independently REVIEWS the gold and flags
issues that human reviewers should see.

What B is asked to do:

* Confirm each ``supporting_claim_id`` in the pool is genuinely relevant to the
  ``seed_topic``.
* Confirm the pool is large/diverse enough for ``supporting_claim_ids_min``.
* Confirm the ``forbidden_substrings`` are reasonable (verbatim from articles,
  not so generic they trap any answer).
* If ``reference_hypothesis_optional`` is present, sanity-check it against the
  pool and topic.

The matcher converts B's structured review into a single ``priority``: any pool
issue (irrelevant claim, insufficient pool) escalates to high; gates issues to
medium; full agreement to low.
"""

from __future__ import annotations

import json
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

IDEA_ASSIST_SYSTEM_PROMPT = (
    "You are an independent reviewer of a research-idea-assistant benchmark "
    "fixture. The fixture defines: a research topic, a pool of supporting facts "
    "(by id), a list of forbidden verbatim phrases, and constraints. Your job is "
    "to flag any inadequacy in the fixture so a human reviewer can fix it. "
    "Always answer with a JSON object."
)

IDEA_ASSIST_USER_PROMPT_TEMPLATE = """Review the following idea-assist gold fixture.

For each supporting claim in the pool, decide if it is relevant to the seed topic.
Then evaluate the pool size, the forbidden substrings, and (if present) the
optional reference hypothesis. Be conservative: if you would not flag it, mark it OK.

Output strictly this JSON object — no prose, no markdown:
{{
  "pool_relevance": [
    {{"claim_id": "<id>", "relevance": "high"|"medium"|"low"|"unknown", "rationale": "<one sentence>"}}
  ],
  "pool_sufficiency": "sufficient" | "thin" | "insufficient",
  "pool_sufficiency_rationale": "<one sentence>",
  "forbidden_substrings_quality": "appropriate" | "too_strict" | "too_loose" | "unknown",
  "forbidden_substrings_rationale": "<one sentence>",
  "reference_hypothesis_quality": "plausible" | "thin" | "unrealistic" | "absent",
  "reference_hypothesis_rationale": "<one sentence>",
  "overall_assessment": "ok" | "needs_revision",
  "issues": ["<short bullet>", "..."]
}}

GOLD FIXTURE:
- seed_topic: {seed_topic}
- supporting_claim_ids_min: {supporting_claim_ids_min}
- supporting_claim_id_pool:
{pool_block}
- forbidden_substrings:
{forbidden_block}
- max_rouge_l_against_evidence_quotes: {max_rouge_l}
- novelty_must_reference_gap: {novelty_must_reference_gap}
- reference_hypothesis_optional: {reference_hypothesis}

SUPPORTING CLAIM TEXTS (from claims gold packs):
{claim_texts_block}
"""

_VALID_RELEVANCE = {"high", "medium", "low", "unknown"}
_VALID_POOL = {"sufficient", "thin", "insufficient"}
_VALID_FORBIDDEN = {"appropriate", "too_strict", "too_loose", "unknown"}
_VALID_REFHYP = {"plausible", "thin", "unrealistic", "absent"}
_VALID_OVERALL = {"ok", "needs_revision"}


class IdeaPoolRelevanceModel(BaseModel):
    claim_id: str = Field(default="")
    relevance: str = Field(default="unknown")
    rationale: str = Field(default="")


class IdeaAssistResponseModel(BaseModel):
    pool_relevance: list[IdeaPoolRelevanceModel] = Field(default_factory=list)
    pool_sufficiency: str = Field(default="sufficient")
    pool_sufficiency_rationale: str = Field(default="")
    forbidden_substrings_quality: str = Field(default="appropriate")
    forbidden_substrings_rationale: str = Field(default="")
    reference_hypothesis_quality: str = Field(default="absent")
    reference_hypothesis_rationale: str = Field(default="")
    overall_assessment: str = Field(default="ok")
    issues: list[str] = Field(default_factory=list)


class IdeaAssistLiveExtractor(ExtractorBase):
    """Independent LLM reviewer for ``idea_assist_v1/live_*`` packs."""

    layer_name = "idea_assist_live"
    response_model = IdeaAssistResponseModel

    def discover_packs(self, fixtures_root: Path) -> list[Path]:
        base = fixtures_root / "idea_assist_v1"
        return sorted(d for d in base.glob("live_*") if (d / "gold.json").exists())

    def _load_claim_texts(
        self,
        pack_dir: Path,
        claim_ids: list[str],
    ) -> dict[str, str]:
        """Walk every claims pack to resolve `claim_id -> claim_text_normalized`.

        We do this once per pack invocation; ~20 packs × ~5 claims is cheap and
        keeps the extractor self-contained (no shared cache needed).
        """

        claims_root = pack_dir.parent.parent / "claims"
        if not claims_root.exists():
            return {}
        wanted = set(claim_ids)
        out: dict[str, str] = {}
        for gold_path in claims_root.glob("**/gold.json"):
            try:
                gold = json.loads(gold_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            for c in gold.get("expected_claims", []):
                cid = c.get("claim_id")
                if cid in wanted and cid not in out:
                    out[cid] = c.get("claim_text_normalized", "")
            if len(out) == len(wanted):
                break
        return out

    def build_call_spec(self, pack_dir: Path, *, model: str, base_url: str) -> LLMCallSpec:
        gold = json.loads((pack_dir / "gold.json").read_text(encoding="utf-8"))
        pool = list(gold.get("supporting_claim_id_pool", []))
        forbidden = list(gold.get("forbidden_substrings", []))
        claim_texts = self._load_claim_texts(pack_dir, pool)
        pool_block = "\n".join(f"  - {cid}" for cid in pool) or "  (empty)"
        forbidden_block = "\n".join(f'  - "{s[:160]}"' for s in forbidden) or "  (empty)"
        claim_texts_block = (
            "\n".join(
                f"  - {cid}: {claim_texts.get(cid, '<NOT FOUND in claims gold>')}" for cid in pool
            )
            or "  (no claims found)"
        )
        user = IDEA_ASSIST_USER_PROMPT_TEMPLATE.format(
            seed_topic=gold.get("seed_topic", ""),
            supporting_claim_ids_min=gold.get("supporting_claim_ids_min", 0),
            pool_block=pool_block,
            forbidden_block=forbidden_block,
            max_rouge_l=gold.get("max_rouge_l_against_evidence_quotes", "n/a"),
            novelty_must_reference_gap=gold.get("novelty_must_reference_gap", False),
            reference_hypothesis=gold.get("reference_hypothesis_optional", "<absent>"),
            claim_texts_block=claim_texts_block,
        )
        return LLMCallSpec(
            model=model,
            base_url=base_url,
            system_prompt=IDEA_ASSIST_SYSTEM_PROMPT,
            user_prompt=user,
            temperature=0.1,
            max_tokens=1500,
            response_format="json_object",
        )

    def parse_response(self, raw_response: str) -> list[dict]:
        obj = self._safe_parse(raw_response)
        if not isinstance(obj, dict):
            raise ValueError("extractor B response: top-level must be a JSON object")
        pool_raw = obj.get("pool_relevance") or []
        pool_clean: list[dict] = []
        for entry in pool_raw:
            if not isinstance(entry, dict):
                continue
            rel = (entry.get("relevance") or "").strip().lower()
            if rel not in _VALID_RELEVANCE:
                rel = "unknown"
            pool_clean.append(
                {
                    "claim_id": (entry.get("claim_id") or "").strip(),
                    "relevance": rel,
                    "rationale": (entry.get("rationale") or "").strip()[:300],
                }
            )

        def _enum(value: Any, allowed: set[str], default: str) -> str:
            v = (value or "").strip().lower()
            return v if v in allowed else default

        issues_raw = obj.get("issues") or []
        issues = [str(i).strip() for i in issues_raw if str(i).strip()]
        return [
            {
                "pool_relevance": pool_clean,
                "pool_sufficiency": _enum(obj.get("pool_sufficiency"), _VALID_POOL, "sufficient"),
                "pool_sufficiency_rationale": (obj.get("pool_sufficiency_rationale") or "")[:400],
                "forbidden_substrings_quality": _enum(
                    obj.get("forbidden_substrings_quality"), _VALID_FORBIDDEN, "appropriate"
                ),
                "forbidden_substrings_rationale": (obj.get("forbidden_substrings_rationale") or "")[
                    :400
                ],
                "reference_hypothesis_quality": _enum(
                    obj.get("reference_hypothesis_quality"), _VALID_REFHYP, "absent"
                ),
                "reference_hypothesis_rationale": (obj.get("reference_hypothesis_rationale") or "")[
                    :400
                ],
                "overall_assessment": _enum(obj.get("overall_assessment"), _VALID_OVERALL, "ok"),
                "issues": issues,
            }
        ]

    @staticmethod
    def _classify_priority(review: dict) -> tuple[str, str]:
        low_relevance = sum(1 for e in review["pool_relevance"] if e["relevance"] == "low")
        if low_relevance >= 1 or review["pool_sufficiency"] == "insufficient":
            return (
                "high",
                f"low_relevance_in_pool={low_relevance}, pool={review['pool_sufficiency']}",
            )
        if (
            review["pool_sufficiency"] == "thin"
            or review["forbidden_substrings_quality"] in {"too_strict", "too_loose"}
            or review["reference_hypothesis_quality"] in {"thin", "unrealistic"}
            or review["overall_assessment"] == "needs_revision"
        ):
            return (
                "medium",
                f"pool={review['pool_sufficiency']}, forbidden={review['forbidden_substrings_quality']}, "
                f"refhyp={review['reference_hypothesis_quality']}, overall={review['overall_assessment']}",
            )
        return (
            "low",
            "all dimensions ok per extractor B (sufficient/appropriate/plausible/ok)",
        )

    def build_report(
        self,
        pack_dir: Path,
        *,
        run: ExtractorRunOutput | None,
        gold_a: dict,
        embedding_scorer: EmbeddingScorerProtocol | None = None,  # noqa: ARG002 — review-only
    ) -> ConsistencyReport:
        a_pool = list(gold_a.get("supporting_claim_id_pool", []))
        review = run.structured_b[0] if (run is not None and run.structured_b) else None

        matched_pairs: list[dict[str, Any]] = []
        unmatched_a: list[dict[str, Any]] = []
        unmatched_b: list[dict[str, Any]] = []
        if review is not None:
            for cid in a_pool:
                hit = next(
                    (e for e in review["pool_relevance"] if e["claim_id"] == cid),
                    None,
                )
                if hit is None:
                    unmatched_a.append(
                        {
                            "claim_id": cid,
                            "comment": "claim id present in gold pool but not reviewed by B",
                        }
                    )
                else:
                    matched_pairs.append(
                        {
                            "claim_id": cid,
                            "match_score": 1.0,
                            "match_source": "claim_id_exact",
                            "b_relevance": hit["relevance"],
                            "b_rationale": hit["rationale"],
                            "field_disagreements": (
                                [
                                    {
                                        "field": "relevance",
                                        "a": "implicit_high",
                                        "b": hit["relevance"],
                                    }
                                ]
                                if hit["relevance"] in {"low", "unknown"}
                                else []
                            ),
                        }
                    )
            for entry in review["pool_relevance"]:
                if entry["claim_id"] not in set(a_pool):
                    unmatched_b.append(
                        {
                            "claim_id": entry["claim_id"],
                            "b_relevance": entry["relevance"],
                            "comment": "B reviewed a claim_id that is not in the gold pool",
                        }
                    )
            review_block: dict[str, Any] = {
                "pool_sufficiency": review["pool_sufficiency"],
                "pool_sufficiency_rationale": review["pool_sufficiency_rationale"],
                "forbidden_substrings_quality": review["forbidden_substrings_quality"],
                "forbidden_substrings_rationale": review["forbidden_substrings_rationale"],
                "reference_hypothesis_quality": review["reference_hypothesis_quality"],
                "reference_hypothesis_rationale": review["reference_hypothesis_rationale"],
                "overall_assessment": review["overall_assessment"],
                "issues": review["issues"],
            }
            priority, why = self._classify_priority(review)
        else:
            for cid in a_pool:
                unmatched_a.append({"claim_id": cid, "comment": "dry-run: no B review"})
            review_block = {}
            priority, why = ("medium", "dry-run: no extractor B review available")

        rel_pack, rel_gold = self._safe_relative_paths(pack_dir)

        a_info = ExtractorInfo(
            role="human_authored_existing_gold",
            source=str(rel_gold),
            count=len(a_pool),
        )
        b_info = self._extractor_b_info(
            run,
            role="llm_independent_reviewer",
            source="gold fixture review (not output generation)",
            count=len(matched_pairs) + len(unmatched_b),
            dry_run_role="llm_independent_reviewer_dry_run",
        )

        summary = self._summary_skeleton(
            a_total=len(a_pool),
            b_total=len(matched_pairs) + len(unmatched_b),
            matched_pairs=matched_pairs,
            unmatched_a=unmatched_a,
            unmatched_b=unmatched_b,
            extra={"review": review_block},
        )
        return ConsistencyReport(
            pack_id=f"idea_assist_v1/{pack_dir.name}",
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
