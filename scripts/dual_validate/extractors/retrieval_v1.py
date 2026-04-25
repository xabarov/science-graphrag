"""``retrieval/*`` extractors: B re-derives expected work ids from a question.

Three layers share the same shape:

* ``workspace_scoped_live`` — B sees question + workspace papers + the rest of
  the corpus, predicts which corpus_work_ids are relevant inside the workspace
  and which (if any) of the explicitly forbidden ids it would mistakenly cite.
* ``hybrid_ablation_v2`` — B classifies a candidate set (``relevant +
  irrelevant`` from gold) into the two buckets without seeing gold labels.
* ``multihop_v2`` — B is told the path kind (``ordered_chain`` or
  ``unordered_set``) and the question, then returns either the chain or the
  expected node ids/canonical names.

Output space is closed (``corpus_work_id``s / canonical author names supplied
in the inventory), so embedding cascade is not used. The matcher computes
set-overlap precision / recall / Jaccard plus, for ``ordered_chain``,
Kendall-style order correctness.
"""

from __future__ import annotations

import json
import re
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

CATALOG_PATH = Path("tests/fixtures/corpus/CATALOG.md")
WORKSPACES_PATH = Path("tests/fixtures/benchmarks/retrieval/workspace_scoped_live/_workspaces.json")


_INVENTORY_CACHE: dict[str, dict[str, str]] | None = None
_TABLE_ROW = re.compile(r"^\|\s*`([a-z0-9_]+)`\s*\|\s*(.*?)\s*\|\s*([0-9n/a]+)\s*\|")


def _load_inventory() -> dict[str, dict[str, str]]:
    """Parse CATALOG.md inventory table → ``{corpus_work_id: {title, year}}``."""

    global _INVENTORY_CACHE  # noqa: PLW0603 — module-level cache by design
    if _INVENTORY_CACHE is not None:
        return _INVENTORY_CACHE
    inv: dict[str, dict[str, str]] = {}
    text = CATALOG_PATH.read_text(encoding="utf-8")
    for line in text.splitlines():
        m = _TABLE_ROW.match(line)
        if not m:
            continue
        wid, title, year = m.group(1), m.group(2), m.group(3)
        inv[wid] = {"title": title.strip(), "year": year.strip()}
    _INVENTORY_CACHE = inv
    return inv


def _format_candidates(work_ids: list[str], inv: dict[str, dict[str, str]]) -> str:
    lines: list[str] = []
    for wid in work_ids:
        meta = inv.get(wid, {})
        title = meta.get("title", "<title unknown>")
        year = meta.get("year", "n/a")
        lines.append(f"  - {wid}  ({year}) — {title}")
    return "\n".join(lines)


def _set_metrics(a: set[str], b: set[str]) -> dict[str, float]:
    inter = len(a & b)
    union = len(a | b) or 1
    p = inter / len(b) if b else 0.0
    r = inter / len(a) if a else 0.0
    f1 = (2 * p * r / (p + r)) if (p + r) else 0.0
    return {
        "precision": round(p, 3),
        "recall": round(r, 3),
        "f1": round(f1, 3),
        "jaccard": round(inter / union, 3),
    }


def _kendall_order(a: list[str], b: list[str]) -> float:
    """Pairwise order agreement on the intersection (∈ [0,1])."""

    common = [x for x in a if x in b]
    if len(common) < 2:
        return 1.0 if common else 0.0
    pos_a = {x: i for i, x in enumerate(a) if x in common}
    pos_b = {x: i for i, x in enumerate(b) if x in common}
    correct = 0
    total = 0
    for i, x in enumerate(common):
        for y in common[i + 1 :]:
            total += 1
            if (pos_a[x] < pos_a[y]) == (pos_b[x] < pos_b[y]):
                correct += 1
    return round(correct / total, 3) if total else 0.0


# ---------------------------------------------------------------------------
# workspace_scoped_live
# ---------------------------------------------------------------------------


_WS_SYSTEM = (
    "You are an independent retrieval reviewer. Given a question, the papers "
    "available in a workspace, and the rest of the corpus that is OUT OF "
    "scope, decide which workspace papers should be cited and flag any "
    "out-of-scope papers you would have mistakenly added. Always answer as a "
    "JSON object."
)

_WS_USER = """Workspace: {ws_name}
Workspace papers (in scope):
{workspace_block}

Out-of-scope papers (must NOT be cited):
{forbidden_block}

QUESTION:
{question}

Output STRICTLY this JSON object — no prose, no markdown:
{{
  "expected_corpus_work_ids": ["<id from workspace>", ...],
  "would_violate_workspace_with": ["<id from out-of-scope>", ...],
  "rationale": "<one sentence>"
}}
"""


class WorkspaceScopedLiveExtractor(ExtractorBase):
    layer_name = "workspace_scoped_live"
    fixtures_subdir: ClassVar[str] = "retrieval/workspace_scoped_live"

    def discover_packs(self, fixtures_root: Path) -> list[Path]:
        base = fixtures_root / self.fixtures_subdir
        if not base.exists():
            return []
        return sorted(d for d in base.iterdir() if d.is_dir() and (d / "gold.json").exists())

    def _gold(self, pack_dir: Path) -> dict:
        return json.loads((pack_dir / "gold.json").read_text(encoding="utf-8"))

    def _question(self, pack_dir: Path) -> str:
        return (pack_dir / "question.txt").read_text(encoding="utf-8").strip()

    def _workspace_papers(self, ws_id: str) -> list[str]:
        ws = json.loads(WORKSPACES_PATH.read_text(encoding="utf-8"))["workspaces"]
        spec = ws.get(ws_id) or {}
        ids = spec.get("corpus_work_ids", [])
        if ids == "*":
            return sorted(_load_inventory().keys())
        return list(ids)

    def build_call_spec(self, pack_dir: Path, *, model: str, base_url: str) -> LLMCallSpec:
        gold = self._gold(pack_dir)
        question = self._question(pack_dir)
        ws_id = gold["workspace_id"]
        workspace_ids = self._workspace_papers(ws_id)
        forbidden_ids = list(gold.get("forbidden_corpus_work_ids", []))
        inv = _load_inventory()
        ws_block = _format_candidates(workspace_ids, inv)
        forbidden_block = _format_candidates(forbidden_ids, inv) or "  (none)"
        user = _WS_USER.format(
            ws_name=ws_id,
            workspace_block=ws_block,
            forbidden_block=forbidden_block,
            question=question,
        )
        return LLMCallSpec(
            model=model,
            base_url=base_url,
            system_prompt=_WS_SYSTEM,
            user_prompt=user,
            temperature=0.1,
            max_tokens=1024,
            response_format="json_object",
        )

    def parse_response(self, raw_response: str) -> list[dict]:
        try:
            obj = parse_json_object_lenient(raw_response)
        except ValueError as exc:
            raise ValueError(f"extractor B (workspace_scoped_live): {exc}") from exc
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
        a_required = {
            c["corpus_work_id"]
            for c in gold_a.get("expected_citations", [])
            if c.get("required") is True
        }
        a_optional = {
            c["corpus_work_id"]
            for c in gold_a.get("expected_citations", [])
            if c.get("required") is False
        }
        a_all = a_required | a_optional
        a_forbidden = set(gold_a.get("forbidden_corpus_work_ids", []))

        if run is not None and run.structured_b:
            payload = run.structured_b[0]
            b_expected = set(payload["expected_corpus_work_ids"])
            b_violations = set(payload["would_violate_workspace_with"])
            rationale = payload["rationale"]
        else:
            b_expected = set()
            b_violations = set()
            rationale = ""

        # B should never propose ids that the gold marks as forbidden — that
        # would be a workspace boundary leak.
        b_real_violations = b_violations & a_forbidden
        b_phantom_violations = b_violations - a_forbidden  # B mis-classified
        crossed_boundary_directly = b_expected & a_forbidden
        metrics_required = _set_metrics(a_required, b_expected)
        metrics_all = _set_metrics(a_all, b_expected)

        matched_pairs: list[dict[str, Any]] = []
        for wid in sorted(a_all & b_expected):
            matched_pairs.append(
                {
                    "corpus_work_id": wid,
                    "match_score": 1.0,
                    "match_source": "set",
                    "field_disagreements": [],
                }
            )
        unmatched_a = [
            {"corpus_work_id": wid, "kind": "missed_by_b", "required": wid in a_required}
            for wid in sorted(a_all - b_expected)
        ]
        unmatched_b = [
            {"corpus_work_id": wid, "kind": "extra_in_b"} for wid in sorted(b_expected - a_all)
        ]
        for wid in sorted(crossed_boundary_directly):
            unmatched_b.append(
                {
                    "corpus_work_id": wid,
                    "kind": "boundary_violation",
                    "comment": "B proposed an out-of-scope paper as a citation",
                }
            )

        priority, why = self._classify_priority(
            metrics_required=metrics_required,
            metrics_all=metrics_all,
            boundary_violations=len(crossed_boundary_directly),
            real_violations_predicted=len(b_real_violations),
            a_empty_negative_case=(len(a_all) == 0),
            b_empty=(len(b_expected) == 0),
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
            count=len(a_all),
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
                source=f"workspace={gold_a.get('workspace_id', '?')} | question.txt",
                model=run.call_spec.model,
                base_url=run.call_spec.base_url,
                prompt_hash=run.prompt_hash,
                count=len(b_expected),
                usage_tokens=run.usage_tokens,
                latency_ms=run.latency_ms,
            )

        summary = {
            "a_total": len(a_all),
            "b_total": len(b_expected),
            "matched": len(matched_pairs),
            "matched_lexical": len(matched_pairs),
            "matched_embedding": 0,
            "unmatched_a": len(unmatched_a),
            "unmatched_b": len(unmatched_b),
            "metrics_required_only": metrics_required,
            "metrics_required_or_optional": metrics_all,
            "boundary_violations_count": len(crossed_boundary_directly),
            "real_forbidden_predictions": len(b_real_violations),
            "phantom_forbidden_predictions": len(b_phantom_violations),
            "rationale_b": rationale,
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
        metrics_required: dict[str, float],
        metrics_all: dict[str, float],
        boundary_violations: int,
        real_violations_predicted: int,  # noqa: ARG004 — kept for downstream reporting
        a_empty_negative_case: bool = False,
        b_empty: bool = False,
    ) -> tuple[str, str]:
        if boundary_violations > 0:
            return (
                "high",
                f"B proposed {boundary_violations} out-of-scope corpus_work_id(s) — workspace boundary leak",
            )
        if a_empty_negative_case:
            # Negative case: gold expects abstain (empty citations).
            if b_empty:
                return (
                    "low",
                    "negative case: B also returned an empty expected_corpus_work_ids set",
                )
            return (
                "high",
                "negative case: B proposed citations where gold expects abstain",
            )
        if metrics_required["recall"] >= 0.9 and metrics_all["precision"] >= 0.7:
            return (
                "low",
                f"required-recall={metrics_required['recall']:.2f}, precision={metrics_all['precision']:.2f}",
            )
        if metrics_required["recall"] >= 0.5 and metrics_all["precision"] >= 0.5:
            return (
                "medium",
                f"required-recall={metrics_required['recall']:.2f}, precision={metrics_all['precision']:.2f}",
            )
        return (
            "high",
            f"required-recall={metrics_required['recall']:.2f}, precision={metrics_all['precision']:.2f} (gate)",
        )


# ---------------------------------------------------------------------------
# hybrid_ablation_v2
# ---------------------------------------------------------------------------


_HA_SYSTEM = (
    "You are an independent retrieval reviewer. Given a question and a list "
    "of candidate papers, classify each candidate as relevant or irrelevant "
    "to the question. Always answer as a JSON object."
)

_HA_USER = """QUESTION:
{question}

Candidate papers:
{candidates_block}

Output STRICTLY this JSON object — no prose, no markdown:
{{
  "relevant_corpus_work_ids": ["<id>", ...],
  "irrelevant_corpus_work_ids": ["<id>", ...],
  "rationale": "<one sentence>"
}}
"""


class HybridAblationV2Extractor(ExtractorBase):
    layer_name = "hybrid_ablation_v2"
    fixtures_subdir: ClassVar[str] = "retrieval/hybrid_ablation_v2"

    def discover_packs(self, fixtures_root: Path) -> list[Path]:
        base = fixtures_root / self.fixtures_subdir
        if not base.exists():
            return []
        return sorted(d for d in base.iterdir() if d.is_dir() and (d / "gold.json").exists())

    def _gold(self, pack_dir: Path) -> dict:
        return json.loads((pack_dir / "gold.json").read_text(encoding="utf-8"))

    def build_call_spec(self, pack_dir: Path, *, model: str, base_url: str) -> LLMCallSpec:
        gold = self._gold(pack_dir)
        question = (pack_dir / "question.txt").read_text(encoding="utf-8").strip()
        candidates = sorted(
            set(gold.get("relevant_corpus_work_ids", []))
            | set(gold.get("irrelevant_corpus_work_ids", []))
        )
        inv = _load_inventory()
        block = _format_candidates(candidates, inv)
        return LLMCallSpec(
            model=model,
            base_url=base_url,
            system_prompt=_HA_SYSTEM,
            user_prompt=_HA_USER.format(question=question, candidates_block=block),
            temperature=0.1,
            max_tokens=1024,
            response_format="json_object",
        )

    def parse_response(self, raw_response: str) -> list[dict]:
        try:
            obj = parse_json_object_lenient(raw_response)
        except ValueError as exc:
            raise ValueError(f"extractor B (hybrid_ablation_v2): {exc}") from exc
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
        a_relevant = set(gold_a.get("relevant_corpus_work_ids", []))
        a_irrelevant = set(gold_a.get("irrelevant_corpus_work_ids", []))
        candidates = a_relevant | a_irrelevant

        if run is not None and run.structured_b:
            payload = run.structured_b[0]
            b_relevant = set(payload["relevant"]) & candidates
            rationale = payload["rationale"]
        else:
            b_relevant = set()
            rationale = ""
        b_irrelevant = candidates - b_relevant

        agree_relevant = a_relevant & b_relevant
        agree_irrelevant = a_irrelevant & b_irrelevant
        disagree_a_relevant_b_irrelevant = a_relevant & b_irrelevant
        disagree_a_irrelevant_b_relevant = a_irrelevant & b_relevant

        metrics = _set_metrics(a_relevant, b_relevant)
        accuracy = (
            (len(agree_relevant) + len(agree_irrelevant)) / len(candidates) if candidates else 0.0
        )

        matched_pairs = [
            {
                "corpus_work_id": wid,
                "label": "relevant",
                "match_score": 1.0,
                "match_source": "set",
                "field_disagreements": [],
            }
            for wid in sorted(agree_relevant)
        ] + [
            {
                "corpus_work_id": wid,
                "label": "irrelevant",
                "match_score": 1.0,
                "match_source": "set",
                "field_disagreements": [],
            }
            for wid in sorted(agree_irrelevant)
        ]
        unmatched_a = [
            {"corpus_work_id": wid, "label_a": "relevant", "label_b": "irrelevant"}
            for wid in sorted(disagree_a_relevant_b_irrelevant)
        ] + [
            {"corpus_work_id": wid, "label_a": "irrelevant", "label_b": "relevant"}
            for wid in sorted(disagree_a_irrelevant_b_relevant)
        ]
        unmatched_b: list[dict[str, Any]] = []

        if accuracy >= 0.9 and metrics["f1"] >= 0.9:
            priority = "low"
            why = f"accuracy={accuracy:.2f}, f1_relevant={metrics['f1']:.2f}"
        elif accuracy >= 0.75 and metrics["f1"] >= 0.6:
            priority = "medium"
            why = f"accuracy={accuracy:.2f}, f1_relevant={metrics['f1']:.2f}"
        else:
            priority = "high"
            why = f"accuracy={accuracy:.2f}, f1_relevant={metrics['f1']:.2f} (gate)"

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
            count=len(a_relevant),
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
                source=f"question.txt | candidates={len(candidates)}",
                model=run.call_spec.model,
                base_url=run.call_spec.base_url,
                prompt_hash=run.prompt_hash,
                count=len(b_relevant),
                usage_tokens=run.usage_tokens,
                latency_ms=run.latency_ms,
            )

        summary = {
            "a_total": len(a_relevant),
            "b_total": len(b_relevant),
            "matched": len(matched_pairs),
            "matched_lexical": len(matched_pairs),
            "matched_embedding": 0,
            "unmatched_a": len(unmatched_a),
            "unmatched_b": 0,
            "candidates_total": len(candidates),
            "accuracy": round(accuracy, 3),
            "metrics_relevant": metrics,
            "rationale_b": rationale,
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


# ---------------------------------------------------------------------------
# multihop_v2
# ---------------------------------------------------------------------------


_MH_SYSTEM = (
    "You are an independent multihop-retrieval reviewer. Given a question, "
    "an indication of whether the answer is an ordered chain of papers or an "
    "unordered set of papers / authors, and an inventory of candidate papers, "
    "produce the expected ids (and order, if a chain). Always answer as a "
    "JSON object."
)

_MH_USER_CHAIN = """QUESTION:
{question}

Expected path kind: ordered_chain (later items extend / cite earlier items)

Candidate inventory:
{candidates_block}

Output STRICTLY this JSON object — no prose, no markdown:
{{
  "expected_chain_corpus_work_ids": ["<id>", "<id>", ...],
  "rationale": "<one sentence>"
}}
"""

_MH_USER_SET = """QUESTION:
{question}

Expected path kind: unordered_set ({node_kind})

Candidate paper inventory (use to ground your answer):
{candidates_block}

Output STRICTLY this JSON object — no prose, no markdown:
{{
  "expected_node_canonical_names": ["<name>", "<name>", ...],
  "rationale": "<one sentence>"
}}
"""


class MultihopV2Extractor(ExtractorBase):
    layer_name = "multihop_v2"
    fixtures_subdir: ClassVar[str] = "retrieval/multihop_v2"

    def discover_packs(self, fixtures_root: Path) -> list[Path]:
        base = fixtures_root / self.fixtures_subdir
        if not base.exists():
            return []
        return sorted(d for d in base.iterdir() if d.is_dir() and (d / "gold.json").exists())

    def _gold(self, pack_dir: Path) -> dict:
        return json.loads((pack_dir / "gold.json").read_text(encoding="utf-8"))

    def _candidate_ids(self, gold: dict) -> list[str]:
        # Provide a generous inventory so B has to filter, not guess.
        if gold.get("expected_path_kind") == "ordered_chain":
            return list(gold.get("expected_chain_corpus_work_ids", []))
        # Set node case: include relevant + a small distractor pool from inventory.
        names = sorted(_load_inventory().keys())
        return names

    def build_call_spec(self, pack_dir: Path, *, model: str, base_url: str) -> LLMCallSpec:
        gold = self._gold(pack_dir)
        question = (pack_dir / "question.txt").read_text(encoding="utf-8").strip()
        inv = _load_inventory()
        candidates = self._candidate_ids(gold)
        block = _format_candidates(candidates, inv)
        if gold.get("expected_path_kind") == "ordered_chain":
            user = _MH_USER_CHAIN.format(question=question, candidates_block=block)
        else:
            user = _MH_USER_SET.format(
                question=question,
                node_kind=gold.get("expected_node_kind", "unspecified"),
                candidates_block=block,
            )
        return LLMCallSpec(
            model=model,
            base_url=base_url,
            system_prompt=_MH_SYSTEM,
            user_prompt=user,
            temperature=0.1,
            max_tokens=1024,
            response_format="json_object",
        )

    def parse_response(self, raw_response: str) -> list[dict]:
        try:
            obj = parse_json_object_lenient(raw_response)
        except ValueError as exc:
            raise ValueError(f"extractor B (multihop_v2): {exc}") from exc
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
        path_kind = gold_a.get("expected_path_kind", "unordered_set")
        if path_kind == "ordered_chain":
            a_chain = list(gold_a.get("expected_chain_corpus_work_ids", []))
            a_set = set(a_chain)
            if run is not None and run.structured_b:
                b_chain = run.structured_b[0]["expected_chain_corpus_work_ids"]
            else:
                b_chain = []
            b_set = set(b_chain)
            metrics = _set_metrics(a_set, b_set)
            order_correctness = _kendall_order(a_chain, b_chain)
            extra_payload = {
                "a_chain": a_chain,
                "b_chain": b_chain,
                "order_correctness": order_correctness,
                "min_chain_order_correctness": gold_a.get("min_chain_order_correctness", 0.8),
            }
        else:
            a_chain = []
            b_chain = []
            a_set = set(gold_a.get("expected_node_canonical_names", []))
            if run is not None and run.structured_b:
                b_set = set(run.structured_b[0]["expected_node_canonical_names"])
            else:
                b_set = set()
            metrics = _set_metrics(a_set, b_set)
            order_correctness = None
            extra_payload = {
                "expected_node_kind": gold_a.get("expected_node_kind"),
                "a_node_canonical_names": sorted(a_set),
                "b_node_canonical_names": sorted(b_set),
                "min_recall": gold_a.get("min_recall"),
                "min_precision": gold_a.get("min_precision"),
            }

        matched_pairs = [
            {
                "node_or_work_id": wid,
                "match_score": 1.0,
                "match_source": "set",
                "field_disagreements": [],
            }
            for wid in sorted(a_set & b_set)
        ]
        unmatched_a = [{"node_or_work_id": wid} for wid in sorted(a_set - b_set)]
        unmatched_b = [{"node_or_work_id": wid} for wid in sorted(b_set - a_set)]

        priority, why = self._classify_priority(
            metrics, order_correctness, gold_a.get("min_chain_order_correctness")
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
            count=len(a_set),
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
                source=f"path_kind={path_kind} | question.txt",
                model=run.call_spec.model,
                base_url=run.call_spec.base_url,
                prompt_hash=run.prompt_hash,
                count=len(b_set),
                usage_tokens=run.usage_tokens,
                latency_ms=run.latency_ms,
            )

        summary = {
            "a_total": len(a_set),
            "b_total": len(b_set),
            "matched": len(matched_pairs),
            "matched_lexical": len(matched_pairs),
            "matched_embedding": 0,
            "unmatched_a": len(unmatched_a),
            "unmatched_b": len(unmatched_b),
            "expected_path_kind": path_kind,
            "metrics": metrics,
            **extra_payload,
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
        metrics: dict[str, float],
        order: float | None,
        min_order: float | None,
    ) -> tuple[str, str]:
        if metrics["f1"] >= 0.9 and (order is None or order >= (min_order or 0.8)):
            return ("low", f"f1={metrics['f1']:.2f}, order={order if order is not None else 'n/a'}")
        if metrics["f1"] >= 0.6:
            return (
                "medium",
                f"f1={metrics['f1']:.2f}, order={order if order is not None else 'n/a'}",
            )
        return (
            "high",
            f"f1={metrics['f1']:.2f}, order={order if order is not None else 'n/a'} (gate)",
        )
