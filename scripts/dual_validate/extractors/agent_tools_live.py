"""``agent_tools_live`` extractor: B drafts an expected tool plan for Phase 5 cases.

Pack layout (one per case under ``tests/fixtures/benchmarks/agent_tools_v1/live_*``):

    live_<NN>_<slug>/gold.json
    live_<NN>_<slug>/question.txt

Extractor B is asked to act as an *agent designer*: given the question and the
known tool set, produce an expected_tool_sequence + expected_works_corpus_ids +
expected_methods_canonical + a short answer reference. The matcher compares:

* **tool_name sequence** — required-tool recall (set agreement; order is
  encouraged but not strictly checked because LLMs reorder freely);
* **expected_works_corpus_ids** / **expected_methods_canonical** — set overlap;
* **answer_reference_text** — token Jaccard between A and B narratives,
  reported as a ROUGE-like signal (gold pack already constrains the runner with
  ``answer_metric.rouge_l``; here we just measure A↔B agreement).

Negative case ``expected_works_corpus_ids: []`` is treated specially: B is
expected to flag ``out_of_scope`` and likewise return an empty work-id list.
"""

from __future__ import annotations

import json
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
from scripts.dual_validate.matcher import EmbeddingScorerProtocol, jaccard, tokenize


def _answer_token_jaccard(a: str, b: str) -> float:
    return jaccard(tokenize(a), tokenize(b))


KNOWN_TOOLS = (
    "vector_search",
    "cypher_query",
    "idea_search",
    "entity_search",
    "edge_search",
    "cite_works",
    "final_answer",
)


_SYSTEM = (
    "You are an independent agent-design reviewer. Given a question, decide "
    "what tool sequence a research agent should run, which corpus papers and "
    "methods the answer should ground in, and draft a short reference "
    "answer. If the question is out of scope for an object-detection corpus, "
    'set expected_behavior="abstain_or_empty" and leave the work / method '
    "lists empty. Always answer as a JSON object."
)


_USER = """QUESTION:
{question}

Tools available to the agent (use any subset, in the order you'd run them):
{tool_block}

Constraints:
- Use only tool_name values from the list above.
- expected_works_corpus_ids must be drawn from the object-detection corpus catalog (e.g. yolov1, retinanet_focal_realpdf, mask_rcnn_realpdf); if no paper is relevant, return [].
- expected_methods_canonical uses lowercase snake-case method ids (focal_loss, region_proposal_network, ...).
- answer_reference_text: 1-3 short sentences answering the question grounded in the corpus. For unanswerable questions, write an explicit abstain sentence using one of: "no paper", "not in", "out of scope", "n/a".

Output STRICTLY this JSON object — no prose, no markdown:
{{
  "expected_tool_sequence": [{{"tool_name": "<name>"}}, ...],
  "expected_works_corpus_ids": ["<id>", ...],
  "expected_methods_canonical": ["<id>", ...],
  "answer_reference_text": "<1-3 sentences>",
  "expected_behavior": "answer" | "abstain_or_empty"
}}
"""


class AgentToolsLiveExtractor(ExtractorBase):
    """One extractor for all ``live_*`` cases in ``agent_tools_v1``."""

    layer_name = "agent_tools_live"
    fixtures_subdir: ClassVar[str] = "agent_tools_v1"

    def discover_packs(self, fixtures_root: Path) -> list[Path]:
        base = fixtures_root / self.fixtures_subdir
        if not base.exists():
            return []
        return sorted(
            d
            for d in base.iterdir()
            if d.is_dir() and d.name.startswith("live_") and (d / "gold.json").exists()
        )

    def _gold(self, pack_dir: Path) -> dict:
        return json.loads((pack_dir / "gold.json").read_text(encoding="utf-8"))

    def build_call_spec(self, pack_dir: Path, *, model: str, base_url: str) -> LLMCallSpec:
        question = (pack_dir / "question.txt").read_text(encoding="utf-8").strip()
        tool_block = "\n".join(f"  - {t}" for t in KNOWN_TOOLS)
        return LLMCallSpec(
            model=model,
            base_url=base_url,
            system_prompt=_SYSTEM,
            user_prompt=_USER.format(question=question, tool_block=tool_block),
            temperature=0.1,
            max_tokens=1024,
            response_format="json_object",
        )

    def parse_response(self, raw_response: str) -> list[dict]:
        try:
            obj = parse_json_object_lenient(raw_response)
        except ValueError as exc:
            raise ValueError(f"extractor B (agent_tools_live): {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError("extractor B response: top-level must be a JSON object")
        tool_seq_raw = obj.get("expected_tool_sequence") or []
        tools: list[str] = []
        for item in tool_seq_raw:
            if isinstance(item, dict) and isinstance(item.get("tool_name"), str):
                tools.append(item["tool_name"])
            elif isinstance(item, str):
                tools.append(item)
        return [
            {
                "tool_sequence": tools,
                "expected_works_corpus_ids": [
                    str(x)
                    for x in (obj.get("expected_works_corpus_ids") or [])
                    if isinstance(x, str)
                ],
                "expected_methods_canonical": [
                    str(x)
                    for x in (obj.get("expected_methods_canonical") or [])
                    if isinstance(x, str)
                ],
                "answer_reference_text": str(obj.get("answer_reference_text") or "").strip(),
                "expected_behavior": str(obj.get("expected_behavior") or "answer").strip(),
            }
        ]

    def build_report(
        self,
        pack_dir: Path,
        *,
        run: ExtractorRunOutput | None,
        gold_a: dict,
        embedding_scorer: EmbeddingScorerProtocol | None = None,  # noqa: ARG002 — set / token diff
    ) -> ConsistencyReport:
        a_tools_required = [
            t["tool_name"]
            for t in gold_a.get("expected_tool_sequence", [])
            if t.get("required") is True
        ]
        a_tools_all = [t["tool_name"] for t in gold_a.get("expected_tool_sequence", [])]
        a_works = set(gold_a.get("expected_works_corpus_ids", []) or [])
        a_methods = set(gold_a.get("expected_methods_canonical", []) or [])
        a_answer = str(gold_a.get("answer_reference_text") or "")
        a_behavior = str(gold_a.get("expected_behavior") or "answer")

        if run is not None and run.structured_b:
            payload = run.structured_b[0]
            b_tools = payload["tool_sequence"]
            b_works = set(payload["expected_works_corpus_ids"])
            b_methods = set(payload["expected_methods_canonical"])
            b_answer = payload["answer_reference_text"]
            b_behavior = payload["expected_behavior"]
        else:
            b_tools = []
            b_works = set()
            b_methods = set()
            b_answer = ""
            b_behavior = "answer"

        # Required-tool recall (B must use every required tool at least once;
        # extra tools allowed since plans differ across LLMs).
        a_req_set = set(a_tools_required)
        b_set = set(b_tools)
        tool_required_recall = len(a_req_set & b_set) / len(a_req_set) if a_req_set else 1.0
        tool_all_recall = (
            len(set(a_tools_all) & b_set) / len(set(a_tools_all)) if a_tools_all else 1.0
        )
        tool_extra = sorted(b_set - set(a_tools_all))
        tool_missing_required = sorted(a_req_set - b_set)

        works_overlap = (
            len(a_works & b_works) / len(a_works | b_works) if (a_works or b_works) else 1.0
        )
        methods_overlap = (
            len(a_methods & b_methods) / len(a_methods | b_methods)
            if (a_methods or b_methods)
            else 1.0
        )
        answer_overlap = _answer_token_jaccard(a_answer, b_answer)

        is_negative = a_behavior == "abstain_or_empty" or len(a_works) == 0
        behavior_agreement = (
            (b_behavior == "abstain_or_empty" and len(b_works) == 0)
            if is_negative
            else (b_behavior == "answer")
        )

        matched_pairs: list[dict[str, Any]] = []
        for t in sorted(a_req_set & b_set):
            matched_pairs.append(
                {
                    "tool_name": t,
                    "kind": "required_tool_match",
                    "match_score": 1.0,
                    "match_source": "set",
                    "field_disagreements": [],
                }
            )
        for w in sorted(a_works & b_works):
            matched_pairs.append(
                {
                    "corpus_work_id": w,
                    "kind": "expected_work_match",
                    "match_score": 1.0,
                    "match_source": "set",
                    "field_disagreements": [],
                }
            )
        for m in sorted(a_methods & b_methods):
            matched_pairs.append(
                {
                    "method_canonical": m,
                    "kind": "expected_method_match",
                    "match_score": 1.0,
                    "match_source": "set",
                    "field_disagreements": [],
                }
            )

        unmatched_a: list[dict[str, Any]] = []
        for t in tool_missing_required:
            unmatched_a.append({"tool_name": t, "kind": "required_tool_missing_in_b"})
        for w in sorted(a_works - b_works):
            unmatched_a.append({"corpus_work_id": w, "kind": "expected_work_missing_in_b"})
        for m in sorted(a_methods - b_methods):
            unmatched_a.append({"method_canonical": m, "kind": "expected_method_missing_in_b"})

        unmatched_b: list[dict[str, Any]] = []
        for t in tool_extra:
            unmatched_b.append({"tool_name": t, "kind": "extra_tool_in_b"})
        for w in sorted(b_works - a_works):
            unmatched_b.append({"corpus_work_id": w, "kind": "extra_work_in_b"})
        for m in sorted(b_methods - a_methods):
            unmatched_b.append({"method_canonical": m, "kind": "extra_method_in_b"})

        priority, why = self._classify_priority(
            tool_required_recall=tool_required_recall,
            works_overlap=works_overlap,
            methods_overlap=methods_overlap,
            answer_overlap=answer_overlap,
            is_negative=is_negative,
            behavior_agreement=behavior_agreement,
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
            count=len(a_tools_all) + len(a_works) + len(a_methods),
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
                source=f"question.txt | tool_set={len(KNOWN_TOOLS)}",
                model=run.call_spec.model,
                base_url=run.call_spec.base_url,
                prompt_hash=run.prompt_hash,
                count=len(b_tools) + len(b_works) + len(b_methods),
                usage_tokens=run.usage_tokens,
                latency_ms=run.latency_ms,
            )

        summary = {
            "a_total": len(a_tools_all) + len(a_works) + len(a_methods),
            "b_total": len(b_tools) + len(b_works) + len(b_methods),
            "matched": len(matched_pairs),
            "matched_lexical": len(matched_pairs),
            "matched_embedding": 0,
            "unmatched_a": len(unmatched_a),
            "unmatched_b": len(unmatched_b),
            "tool_metrics": {
                "required_recall": round(tool_required_recall, 3),
                "all_recall": round(tool_all_recall, 3),
                "missing_required": tool_missing_required,
                "extra_tools_in_b": tool_extra,
            },
            "works_jaccard": round(works_overlap, 3),
            "methods_jaccard": round(methods_overlap, 3),
            "answer_token_jaccard": round(answer_overlap, 3),
            "is_negative_case": is_negative,
            "behavior_agreement": behavior_agreement,
            "behavior_a": a_behavior,
            "behavior_b": b_behavior,
        }
        return ConsistencyReport(
            pack_id=pack_dir.name,
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

    @staticmethod
    def _classify_priority(
        *,
        tool_required_recall: float,
        works_overlap: float,
        methods_overlap: float,
        answer_overlap: float,
        is_negative: bool,
        behavior_agreement: bool,
    ) -> tuple[str, str]:
        if is_negative:
            if behavior_agreement and tool_required_recall >= 1.0:
                return (
                    "low",
                    "negative case: B abstained, required tools matched",
                )
            return (
                "high",
                f"negative case: behavior_agreement={behavior_agreement}, "
                f"required_tool_recall={tool_required_recall:.2f}",
            )
        if (
            tool_required_recall >= 1.0
            and works_overlap >= 0.5
            and methods_overlap >= 0.5
            and answer_overlap >= 0.15
        ):
            return (
                "low",
                f"tool_req_recall={tool_required_recall:.2f}, works={works_overlap:.2f}, "
                f"methods={methods_overlap:.2f}, answer_jaccard={answer_overlap:.2f}",
            )
        if tool_required_recall >= 0.5 and (works_overlap >= 0.3 or methods_overlap >= 0.3):
            return (
                "medium",
                f"tool_req_recall={tool_required_recall:.2f}, works={works_overlap:.2f}, "
                f"methods={methods_overlap:.2f}",
            )
        return (
            "high",
            f"tool_req_recall={tool_required_recall:.2f}, works={works_overlap:.2f}, "
            f"methods={methods_overlap:.2f} (gate)",
        )
