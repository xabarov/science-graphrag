"""``claims_v2`` layer extractor: extractor B re-derives claims from ``article.md``.

Pack layout:

    tests/fixtures/benchmarks/claims/corpus_<slug>_v2/gold.json
    tests/fixtures/benchmarks/layer1/<slug>/article.md   (extractor input)

Extractor A is the existing human-authored gold; extractor B is one independent LLM
pass over the same source article. The matcher diffs the two and writes
``consistency_report.json`` next to the pack.
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
from scripts.dual_validate.extractors.base import ExtractorBase, ExtractorRunOutput
from scripts.dual_validate.llm_client import LLMCallSpec
from scripts.dual_validate.matcher import (
    EmbeddingScorerProtocol,
    MatchResult,
    Record,
    classify_spot_check_priority,
    match_records,
)

CLAIMS_V2_SYSTEM_PROMPT = (
    "You are an independent scientific-claims extractor. "
    "Your output is compared against a separately authored human gold to surface "
    "disagreements for human spot-check, NOT to reproduce that gold. "
    "Be cautious: a claim must be grounded in a verbatim quote from the article. "
    "Always answer with a JSON object."
)

CLAIMS_V2_USER_PROMPT_TEMPLATE = """Extract atomic factual claims from the research paper below.

Each claim MUST be:
- atomic (one fact per claim, not a multi-part statement);
- evidence-grounded (a verbatim short quote from the article supports it);
- typed: exactly one of {{method, performance, comparison, finding, limitation, dataset}};
- polarized: positive (the paper claims X holds / works), negative (the paper claims X fails / has a limitation), or neutral (descriptive only — no claim that X holds or fails);
- normalized: ONE well-formed declarative English sentence, 15-300 chars, no list items, no parenthetical citations.

Extract between 4 and 8 of the most important claims (do not pad). Polarity must reflect what the paper SAYS about the fact, not your opinion.

Output strictly this JSON object — no prose, no markdown:
{{
  "claims": [
    {{
      "claim_text_normalized": "...",
      "claim_type": "method|performance|comparison|finding|limitation|dataset",
      "polarity": "positive|negative|neutral",
      "evidence_quote_short": "<= 200 chars verbatim quote copied from the article"
    }}
  ]
}}

ARTICLE:
=====
{article}
=====
"""

_VALID_TYPES = {"method", "performance", "comparison", "finding", "limitation", "dataset"}
_VALID_POLARITIES = {"positive", "negative", "neutral"}


class ClaimItemModel(BaseModel):
    claim_text_normalized: str = Field(min_length=1)
    claim_type: str = Field(default="finding")
    polarity: str = Field(default="neutral")
    evidence_quote_short: str = Field(default="")


class ClaimsResponseModel(BaseModel):
    claims: list[ClaimItemModel]


class ClaimsV2Extractor(ExtractorBase):
    """Independent LLM extractor over ``article.md`` for ``corpus_<slug>_v2`` packs."""

    layer_name = "claims_v2"
    response_model = ClaimsResponseModel

    def discover_packs(self, fixtures_root: Path) -> list[Path]:
        base = fixtures_root / "claims"
        candidates = list(base.glob("corpus_*_v2")) + list(base.glob("holdout_*_v1"))
        return sorted(d for d in candidates if (d / "gold.json").exists())

    def _resolve_article(self, pack_dir: Path) -> Path:
        gold = json.loads((pack_dir / "gold.json").read_text())
        slug = gold.get("source_layer1_fixture") or gold.get("corpus_work_id")
        if not slug:
            raise ValueError(
                f"{pack_dir.name}: gold.json has neither source_layer1_fixture nor corpus_work_id"
            )
        article = pack_dir.parent.parent / "layer1" / slug / "article.md"
        if not article.exists():
            raise FileNotFoundError(f"{pack_dir.name}: article not found at {article}")
        return article

    def build_call_spec(self, pack_dir: Path, *, model: str, base_url: str) -> LLMCallSpec:
        article = self._resolve_article(pack_dir)
        text = article.read_text()
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text[:60000]
        user = CLAIMS_V2_USER_PROMPT_TEMPLATE.format(article=text)
        return LLMCallSpec(
            model=model,
            base_url=base_url,
            system_prompt=CLAIMS_V2_SYSTEM_PROMPT,
            user_prompt=user,
            temperature=0.1,
            max_tokens=2048,
            response_format="json_object",
        )

    def parse_response(self, raw_response: str) -> list[dict]:
        obj = self._safe_parse_json(raw_response, context="claims")
        claims_raw = obj.get("claims") if isinstance(obj, dict) else obj
        if not isinstance(claims_raw, list):
            raise ValueError("extractor B response: missing/invalid 'claims' list")
        cleaned: list[dict] = []
        for i, c in enumerate(claims_raw):
            if not isinstance(c, dict):
                continue
            text = (c.get("claim_text_normalized") or "").strip()
            ctype = (c.get("claim_type") or "").strip().lower()
            polarity = (c.get("polarity") or "").strip().lower()
            evidence = (c.get("evidence_quote_short") or "").strip()
            if not text:
                continue
            if ctype not in _VALID_TYPES:
                ctype = "finding"
            if polarity not in _VALID_POLARITIES:
                polarity = "neutral"
            cleaned.append(
                {
                    "claim_text_normalized": text,
                    "claim_type": ctype,
                    "polarity": polarity,
                    "evidence_quote_short": evidence[:300],
                    "b_index": i,
                }
            )
        return cleaned

    def _records_a(self, gold_a: dict) -> list[Record]:
        out: list[Record] = []
        for c in gold_a.get("expected_claims", []):
            out.append(
                Record(
                    record_id=c["claim_id"],
                    text=c.get("claim_text_normalized", ""),
                    fields={
                        "polarity": c.get("polarity", ""),
                        "claim_type": c.get("claim_type", ""),
                    },
                )
            )
        return out

    def _records_b(self, parsed_b: list[dict]) -> list[Record]:
        out: list[Record] = []
        for i, c in enumerate(parsed_b):
            out.append(
                Record(
                    record_id=f"b_{i:02d}",
                    text=c["claim_text_normalized"],
                    fields={
                        "polarity": c["polarity"],
                        "claim_type": c["claim_type"],
                    },
                )
            )
        return out

    def _summary(
        self,
        a: list[Record],
        b: list[Record],
        match: MatchResult,
    ) -> dict[str, Any]:
        polarity_agree = polarity_disagree = 0
        type_agree = type_disagree = 0
        lexical_matches = embedding_matches = 0
        for p in match.pairs:
            disagreed_fields = {d["field"] for d in p.field_disagreements}
            if "polarity" in disagreed_fields:
                polarity_disagree += 1
            else:
                polarity_agree += 1
            if "claim_type" in disagreed_fields:
                type_disagree += 1
            else:
                type_agree += 1
            if p.score_source == "embedding":
                embedding_matches += 1
            else:
                lexical_matches += 1
        return {
            "a_total": len(a),
            "b_total": len(b),
            "matched": len(match.pairs),
            "matched_lexical": lexical_matches,
            "matched_embedding": embedding_matches,
            "unmatched_a": len(match.unmatched_a),
            "unmatched_b": len(match.unmatched_b),
            "field_agreements": {
                "polarity": {"agreed": polarity_agree, "disagreed": polarity_disagree},
                "claim_type": {"agreed": type_agree, "disagreed": type_disagree},
            },
        }

    def build_report(
        self,
        pack_dir: Path,
        *,
        run: ExtractorRunOutput | None,
        gold_a: dict,
        embedding_scorer: EmbeddingScorerProtocol | None = None,
    ) -> ConsistencyReport:
        a_records = self._records_a(gold_a)
        if run is None:
            b_records: list[Record] = []
            parsed_b: list[dict] = []
        else:
            parsed_b = run.structured_b
            b_records = self._records_b(parsed_b)
        match = match_records(a_records, b_records, embedding_scorer=embedding_scorer)
        priority, why = classify_spot_check_priority(match, a_total=len(a_records))

        a_text_by_id = {r.record_id: r.text for r in a_records}
        a_fields_by_id = {r.record_id: r.fields for r in a_records}
        b_text_by_id = {r.record_id: r.text for r in b_records}
        b_fields_by_id = {r.record_id: r.fields for r in b_records}
        b_idx_by_id = {f"b_{i:02d}": i for i in range(len(b_records))}

        matched_pairs_payload = [
            {
                "a_claim_id": p.a_id,
                "b_index": b_idx_by_id.get(p.b_id, -1),
                "match_score": p.score,
                "match_source": p.score_source,
                "a_claim_text_normalized": a_text_by_id.get(p.a_id, ""),
                "b_claim_text_normalized": b_text_by_id.get(p.b_id, ""),
                "field_disagreements": p.field_disagreements,
            }
            for p in match.pairs
        ]
        unmatched_a_payload = [
            {
                "a_claim_id": rid,
                "a_claim_text_normalized": a_text_by_id.get(rid, ""),
                "a_polarity": a_fields_by_id.get(rid, {}).get("polarity", ""),
                "a_claim_type": a_fields_by_id.get(rid, {}).get("claim_type", ""),
                "comment": "present in human gold A but not produced by independent extractor B",
            }
            for rid in match.unmatched_a
        ]
        unmatched_b_payload = [
            {
                "b_index": b_idx_by_id.get(rid, -1),
                "b_claim_text_normalized": b_text_by_id.get(rid, ""),
                "b_polarity": b_fields_by_id.get(rid, {}).get("polarity", ""),
                "b_claim_type": b_fields_by_id.get(rid, {}).get("claim_type", ""),
                "comment": "produced by independent extractor B but not in human gold A",
            }
            for rid in match.unmatched_b
        ]

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
            count=len(a_records),
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
                source="article.md (re-extracted)",
                model=run.call_spec.model,
                base_url=run.call_spec.base_url,
                prompt_hash=run.prompt_hash,
                count=len(b_records),
                usage_tokens=run.usage_tokens,
                latency_ms=run.latency_ms,
            )
        return ConsistencyReport(
            pack_id=f"claims/{pack_dir.name}",
            pack_path=str(rel_pack),
            layer=self.layer_name,
            extractor_a=a_info,
            extractor_b=b_info,
            matched_pairs=matched_pairs_payload,
            unmatched_a=unmatched_a_payload,
            unmatched_b=unmatched_b_payload,
            summary=self._summary(a_records, b_records, match),
            spot_check_priority=priority,
            spot_check_priority_rationale=why,
        )
