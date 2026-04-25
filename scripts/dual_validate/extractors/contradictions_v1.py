"""``contradictions_v1`` extractor: B looks for one explicit contradiction per pair.

Pack layout (one per pair):

    tests/fixtures/benchmarks/contradictions_v1/pair_<NN>_<slug>/gold.json
    tests/fixtures/benchmarks/layer1/<slug_a>/article.md
    tests/fixtures/benchmarks/layer1/<slug_b>/article.md

Extractor B receives both source articles and has to either confirm a
contradiction along the same axis as the gold (``contradiction_type``) or report
``contradiction_found = false``. The matcher diffs:

* presence (B confirmed vs gold has it),
* type (era_shift / design_paradigm / post_processing / architectural /
  classical_vs_deep / scaling),
* severity (direct / nuanced),
* claim text similarity (lexical + optional embedding cascade against gold's
  ``claim_a.claim_text`` and ``claim_b.claim_text``).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

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
from scripts.dual_validate.matcher import (
    EmbeddingScorerProtocol,
    char_overlap_coefficient,
    jaccard,
    tokenize,
)

CONTRADICTIONS_SYSTEM_PROMPT = (
    "You are an independent contradiction-finder. Given two research articles, "
    "decide whether they make conflicting claims about the SAME subject (an "
    "era_shift, design_paradigm, post_processing, architectural, classical_vs_deep, "
    "or scaling axis). Be conservative: false positives are worse than false "
    "negatives. Always answer with a JSON object."
)

CONTRADICTIONS_USER_PROMPT_TEMPLATE = """Two research papers below: ARTICLE_A and ARTICLE_B.

Find AT MOST ONE direct or nuanced contradiction between them about the SAME subject.
If you can't find one anchored in verbatim quotes from BOTH papers, return contradiction_found=false.

Allowed types: "era_shift", "design_paradigm", "post_processing", "architectural", "classical_vs_deep", "scaling".
Allowed severities: "direct" (logically opposite claims), "nuanced" (era/context-dependent disagreement).

Output strictly this JSON object — no prose, no markdown:
{{
  "contradiction_found": true|false,
  "claim_a_text": "<one declarative sentence summarising A's position>",
  "claim_b_text": "<one declarative sentence summarising B's position>",
  "claim_a_quote": "<verbatim quote from ARTICLE_A, <=200 chars>",
  "claim_b_quote": "<verbatim quote from ARTICLE_B, <=200 chars>",
  "contradiction_type": "<one of the allowed types or empty string>",
  "severity": "direct" | "nuanced" | "",
  "rationale": "<one or two sentences explaining why this is a contradiction>"
}}

If contradiction_found=false, set claim_a_text/claim_b_text/quotes to "" and contradiction_type/severity to "".

ARTICLE_A:
=====
{article_a}
=====

ARTICLE_B:
=====
{article_b}
=====
"""

_VALID_TYPES = {
    "era_shift",
    "design_paradigm",
    "post_processing",
    "architectural",
    "classical_vs_deep",
    "scaling",
}
_VALID_SEVERITIES = {"direct", "nuanced"}


class ContradictionsV1Extractor(ExtractorBase):
    """Independent LLM extractor for ``contradictions_v1/pair_*`` packs."""

    layer_name = "contradictions_v1"

    def discover_packs(self, fixtures_root: Path) -> list[Path]:
        base = fixtures_root / "contradictions_v1"
        return sorted(d for d in base.glob("pair_*") if (d / "gold.json").exists())

    def _resolve_articles(self, pack_dir: Path) -> tuple[Path, Path, dict, dict]:
        gold = json.loads((pack_dir / "gold.json").read_text(encoding="utf-8"))
        claim_a = gold.get("claim_a") or {}
        claim_b = gold.get("claim_b") or {}
        slug_a = claim_a.get("corpus_work_id")
        slug_b = claim_b.get("corpus_work_id")
        if not slug_a or not slug_b:
            raise ValueError(f"{pack_dir.name}: gold.json missing corpus_work_id on a/b")
        layer1 = pack_dir.parent.parent / "layer1"
        article_a = layer1 / slug_a / "article.md"
        article_b = layer1 / slug_b / "article.md"
        if not article_a.exists():
            raise FileNotFoundError(f"{pack_dir.name}: article A not found at {article_a}")
        if not article_b.exists():
            raise FileNotFoundError(f"{pack_dir.name}: article B not found at {article_b}")
        return article_a, article_b, claim_a, claim_b

    def build_call_spec(self, pack_dir: Path, *, model: str, base_url: str) -> LLMCallSpec:
        article_a_path, article_b_path, _, _ = self._resolve_articles(pack_dir)
        text_a = re.sub(r"\n{3,}", "\n\n", article_a_path.read_text(encoding="utf-8"))[:30000]
        text_b = re.sub(r"\n{3,}", "\n\n", article_b_path.read_text(encoding="utf-8"))[:30000]
        user = CONTRADICTIONS_USER_PROMPT_TEMPLATE.format(
            article_a=text_a,
            article_b=text_b,
        )
        return LLMCallSpec(
            model=model,
            base_url=base_url,
            system_prompt=CONTRADICTIONS_SYSTEM_PROMPT,
            user_prompt=user,
            temperature=0.1,
            max_tokens=1500,
            response_format="json_object",
        )

    def parse_response(self, raw_response: str) -> list[dict]:
        try:
            obj = parse_json_object_lenient(raw_response)
        except ValueError as exc:
            raise ValueError(f"extractor B (contradictions_v1): {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError("extractor B response: top-level must be a JSON object")
        found = bool(obj.get("contradiction_found"))
        ctype = (obj.get("contradiction_type") or "").strip()
        severity = (obj.get("severity") or "").strip().lower()
        return [
            {
                "contradiction_found": found,
                "claim_a_text": (obj.get("claim_a_text") or "").strip(),
                "claim_b_text": (obj.get("claim_b_text") or "").strip(),
                "claim_a_quote": (obj.get("claim_a_quote") or "").strip()[:300],
                "claim_b_quote": (obj.get("claim_b_quote") or "").strip()[:300],
                "contradiction_type": ctype if ctype in _VALID_TYPES else "",
                "severity": severity if severity in _VALID_SEVERITIES else "",
                "rationale": (obj.get("rationale") or "").strip()[:600],
            }
        ]

    @staticmethod
    def _claim_score(
        a_text: str,
        b_text: str,
        scorer: EmbeddingScorerProtocol | None,
    ) -> tuple[float, str]:
        lex = max(
            jaccard(tokenize(a_text), tokenize(b_text)),
            char_overlap_coefficient(a_text, b_text, n=4),
        )
        if scorer is None or lex >= 0.50:
            return round(lex, 3), "lexical"
        emb = scorer.score(a_text, b_text)
        if emb >= 0.75 and emb > lex:
            return round(emb, 3), "embedding"
        return round(lex, 3), "lexical"

    @staticmethod
    def _classify_priority(
        *,
        b_found: bool,
        type_match: bool,
        severity_match: bool,
        text_score_a: float,
        text_score_b: float,
    ) -> tuple[str, str]:
        if not b_found:
            return (
                "high",
                "extractor B did not confirm the contradiction " "(unmatched_a=1, unmatched_b=0)",
            )
        if not type_match:
            return (
                "high",
                "B confirmed contradiction but contradiction_type differs from gold",
            )
        worst_text = min(text_score_a, text_score_b)
        if not severity_match or worst_text < 0.30:
            return (
                "medium",
                f"type matches but severity_match={severity_match}, "
                f"worst_claim_text_score={worst_text:.2f} (gate: severity flip OR text<0.30)",
            )
        return (
            "low",
            f"type+severity match, claim text scores>=0.30 "
            f"({text_score_a:.2f}/{text_score_b:.2f})",
        )

    def build_report(
        self,
        pack_dir: Path,
        *,
        run: ExtractorRunOutput | None,
        gold_a: dict,
        embedding_scorer: EmbeddingScorerProtocol | None = None,
    ) -> ConsistencyReport:
        gold_claim_a = (gold_a.get("claim_a") or {}).get("claim_text", "")
        gold_claim_b = (gold_a.get("claim_b") or {}).get("claim_text", "")
        gold_type = (gold_a.get("contradiction_type") or "").strip()
        gold_severity = (gold_a.get("severity") or "").strip().lower()

        b_entry = run.structured_b[0] if (run is not None and run.structured_b) else None
        b_found = bool(b_entry and b_entry.get("contradiction_found"))

        matched_pairs: list[dict[str, Any]] = []
        unmatched_a: list[dict[str, Any]] = []
        unmatched_b: list[dict[str, Any]] = []

        if b_entry is not None and b_found:
            score_a, source_a = self._claim_score(
                gold_claim_a, b_entry.get("claim_a_text", ""), embedding_scorer
            )
            score_b, source_b = self._claim_score(
                gold_claim_b, b_entry.get("claim_b_text", ""), embedding_scorer
            )
            type_match = b_entry.get("contradiction_type") == gold_type
            severity_match = b_entry.get("severity") == gold_severity
            field_disagreements: list[dict[str, str]] = []
            if not type_match:
                field_disagreements.append(
                    {
                        "field": "contradiction_type",
                        "a": gold_type,
                        "b": b_entry.get("contradiction_type", ""),
                    }
                )
            if not severity_match:
                field_disagreements.append(
                    {
                        "field": "severity",
                        "a": gold_severity,
                        "b": b_entry.get("severity", ""),
                    }
                )
            matched_pairs.append(
                {
                    "pair_id": gold_a.get("pair_id"),
                    "match_score": min(score_a, score_b),
                    "match_source": source_a if source_a == source_b else f"{source_a}+{source_b}",
                    "claim_a_score": score_a,
                    "claim_b_score": score_b,
                    "field_disagreements": field_disagreements,
                    "a_claim_a_text": gold_claim_a,
                    "b_claim_a_text": b_entry.get("claim_a_text", ""),
                    "a_claim_b_text": gold_claim_b,
                    "b_claim_b_text": b_entry.get("claim_b_text", ""),
                }
            )
            priority, why = self._classify_priority(
                b_found=True,
                type_match=type_match,
                severity_match=severity_match,
                text_score_a=score_a,
                text_score_b=score_b,
            )
        else:
            unmatched_a.append(
                {
                    "pair_id": gold_a.get("pair_id"),
                    "a_contradiction_type": gold_type,
                    "a_severity": gold_severity,
                    "comment": (
                        "extractor B did not confirm a contradiction " "between the two articles"
                    ),
                }
            )
            if b_entry is not None:
                unmatched_b.append(
                    {
                        "pair_id": "B_returned_empty",
                        "b_rationale": b_entry.get("rationale", ""),
                        "comment": "B returned contradiction_found=false",
                    }
                )
            priority, why = self._classify_priority(
                b_found=False,
                type_match=False,
                severity_match=False,
                text_score_a=0.0,
                text_score_b=0.0,
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
            count=1,
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
                source="article_a.md + article_b.md (paired)",
                model=run.call_spec.model,
                base_url=run.call_spec.base_url,
                prompt_hash=run.prompt_hash,
                count=1 if b_found else 0,
                usage_tokens=run.usage_tokens,
                latency_ms=run.latency_ms,
            )

        # Detect embedding promotion across both claim sides for summary metrics.
        emb_used = any(mp.get("match_source", "").find("embedding") >= 0 for mp in matched_pairs)
        summary = {
            "a_total": 1,
            "b_total": 1 if b_found else 0,
            "matched": len(matched_pairs),
            "matched_lexical": 1 if (matched_pairs and not emb_used) else 0,
            "matched_embedding": 1 if emb_used else 0,
            "unmatched_a": len(unmatched_a),
            "unmatched_b": len(unmatched_b),
            "field_agreements": {
                "contradiction_type": {
                    "agreed": (
                        1
                        if matched_pairs
                        and not any(
                            d["field"] == "contradiction_type"
                            for d in matched_pairs[0].get("field_disagreements", [])
                        )
                        else 0
                    ),
                    "disagreed": sum(
                        1
                        for mp in matched_pairs
                        for d in mp.get("field_disagreements", [])
                        if d["field"] == "contradiction_type"
                    ),
                },
                "severity": {
                    "agreed": (
                        1
                        if matched_pairs
                        and not any(
                            d["field"] == "severity"
                            for d in matched_pairs[0].get("field_disagreements", [])
                        )
                        else 0
                    ),
                    "disagreed": sum(
                        1
                        for mp in matched_pairs
                        for d in mp.get("field_disagreements", [])
                        if d["field"] == "severity"
                    ),
                },
            },
        }
        return ConsistencyReport(
            pack_id=f"contradictions_v1/{pack_dir.name}",
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
