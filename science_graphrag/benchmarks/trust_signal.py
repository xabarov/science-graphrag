"""Trust signal extraction for benchmark artifacts (BT1).

Maps committed ``eval/results/current-*.json`` suites to ``runtime_mode``,
cross-references ``tests/fixtures/benchmarks/**/gold.json`` ``meta.validation_status``,
and surfaces per-case failures for honest ``decision_gate`` criteria.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Final, Literal

RuntimeMode = Literal[
    "live",
    "canned",
    "mock_runtime",
    "synthetic_gold",
    "broken_connection",
    "harness_substring",
    "missing",
    "unknown",
    # Honest infra / contract lanes — excluded from ``PHANTOM_RUNTIME_MODES`` (BT2/BT3).
    "verified_by_sibling_live",
    "infra_skipped",
    "contract_verified",
]

PHANTOM_RUNTIME_MODES: Final[frozenset[str]] = frozenset(
    {
        "canned",
        "mock_runtime",
        "synthetic_gold",
        "broken_connection",
        "harness_substring",
        "missing",
    }
)

# Members that trigger NO-GO when any per-case failure exists (BT1 aggressive scope).
HARD_BLOCK_MEMBER_KEYS: Final[frozenset[str]] = frozenset({"judge_pilot"})

# Relative to ``tests/fixtures/benchmarks/`` — None = skip gold scan for this member.
_GOLD_SUBDIR_BY_MEMBER: Final[dict[str, str | None]] = {
    "merge_safe_contract_mock": None,
    "strict_pilot_mock": None,
    "live_corpus_mini": None,
    "workspace_scoped": "retrieval/workspace_scoped",
    "workspace_scoped_live": "retrieval/workspace_scoped_live",
    "judge_pilot": None,
    "judge_holdout": None,
    "hybrid_ablation": "retrieval/hybrid_ablation_v2",
    "hybrid_ablation_live": "retrieval/hybrid_ablation_v2",
    "live_corpus_holdout": None,
    "multihop_mini": "retrieval/multihop_v2",
    "claims_merge_contract": "claims",
    "claims_mini": "claims",
    "claims_corpus_v2_mini": "claims",
    "claims_pilot": "claims",
    "claims_pilot_production": "claims",
    "claims_paraphrase_pilot": "claims",
    "claims_paraphrase_holdout": "claims",
    "refs_merge_contract": "references_resolution",
    "refs_mini": "references_resolution",
    "refs_graph": "references_resolution",
    "concept_topic_mini": "concept_topic",
    "agent_tools_mini": "agent_tools_v1",
    "agent_tools_judge": None,
    "contradictions_v1_mini": "contradictions_v1",
    "chat_agent_contract": None,
}


def _retrieval_trace(case: dict[str, Any]) -> dict[str, Any]:
    return (
        (case.get("retrieval_trace") or {}) if isinstance(case.get("retrieval_trace"), dict) else {}
    )


def _embedding_model(case: dict[str, Any]) -> str | None:
    trace = _retrieval_trace(case)
    emb = trace.get("embedding")
    if isinstance(emb, dict):
        return str(emb.get("embedding_model") or "")
    if trace.get("embedding_model") is not None:
        return str(trace.get("embedding_model") or "")
    return None


def _cases_from_block(block: dict[str, Any]) -> list[dict[str, Any]]:
    raw = block.get("cases")
    if not isinstance(raw, list):
        return []
    return [c for c in raw if isinstance(c, dict)]


def detect_runtime_mode(
    member_id: str, block: dict[str, Any], cases: list[dict[str, Any]]
) -> RuntimeMode:
    """Infer how trustworthy the suite artifact is (phantom vs live)."""

    if member_id == "chat_agent_contract":
        return "contract_verified"

    if member_id == "workspace_scoped" and block.get("_workspace_scoped_delegated_to_live"):
        return "verified_by_sibling_live"

    if member_id == "hybrid_ablation" and block.get("_hybrid_ablation_delegated_to_live"):
        return "verified_by_sibling_live"

    if member_id == "multihop_mini":
        skip = block.get("last_infra_skip")
        if isinstance(skip, dict) and skip.get("artifact"):
            return "infra_skipped"

    if block.get("error") == "missing_file":
        return "missing"

    meta = block.get("run_metadata") if isinstance(block.get("run_metadata"), dict) else {}

    if member_id in {"judge_pilot", "judge_holdout"}:
        return "live"

    if member_id == "concept_topic_mini":
        extractor = str(meta.get("extractor") or meta.get("extractor_kind") or "").lower()
        summ = block.get("summary") if isinstance(block.get("summary"), dict) else {}
        if isinstance(summ, dict) and not extractor:
            extractor = str(summ.get("extractor") or "").lower()
        if not extractor and cases:
            extractor = str((cases[0] or {}).get("extractor") or "").lower()
        if "harness" in extractor or "anchor" in extractor:
            return "harness_substring"
        if "production" in extractor or "prod" in extractor:
            return "live"
        # Default harness until an explicit production extractor is wired.
        return "harness_substring"

    if member_id == "agent_tools_mini" and cases:
        mockish = 0
        for c in cases:
            if str(c.get("answer") or "").strip() == "mock answer":
                mockish += 1
                continue
            cites = c.get("citations") or []
            if isinstance(cites, list):
                for cite in cites:
                    if isinstance(cite, dict) and str(cite.get("work_id") or "") == "mock-work":
                        mockish += 1
                        break
        if mockish >= max(1, (len(cases) + 1) // 2):
            return "mock_runtime"
        return "live"

    if member_id == "contradictions_v1_mini" and cases:
        # Neo4j relationship verification (BT12); not a mock-runtime suite.
        return "live"

    if member_id == "multihop_mini" and cases:
        broken = sum(
            1
            for c in cases
            if str((c.get("metrics") or {}).get("request_error") or "").startswith("[Errno 111]")
        )
        if broken >= max(1, (len(cases) + 1) // 2):
            return "broken_connection"

    if member_id in {"merge_safe_contract_mock", "strict_pilot_mock", "workspace_scoped"} and cases:
        mock_emb = sum(1 for c in cases if (_embedding_model(c) or "").lower() == "mock")
        if mock_emb >= max(1, (len(cases) + 1) // 2):
            return "canned"

    if member_id == "hybrid_ablation" and cases:
        if meta.get("extraction_llm_model") is None:
            triples = [
                (
                    (c.get("metrics") or {}).get("mrr_vector"),
                    (c.get("metrics") or {}).get("mrr_hybrid"),
                    (c.get("metrics") or {}).get("mrr_delta"),
                )
                for c in cases
            ]
            if (
                all(all(x is not None for x in t) for t in triples)
                and len(set(triples)) == 1
                and len(cases) >= 2
            ):
                return "synthetic_gold"

    if member_id in {"merge_safe_contract_mock", "strict_pilot_mock"}:
        return "canned"

    if member_id in {"claims_paraphrase_pilot", "claims_paraphrase_holdout"} and cases:
        modes = {str(c.get("runtime_mode") or "") for c in cases if isinstance(c, dict)}
        modes.discard("")
        if len(modes) == 1:
            only = next(iter(modes))
            if only in {
                "live",
                "synthetic_gold",
                "mock_runtime",
                "harness_substring",
                "canned",
                "unknown",
            }:
                return only  # type: ignore[return-value]
        if all(bool(c.get("oracle_predictions")) for c in cases if isinstance(c, dict)):
            return "synthetic_gold"

    if meta.get("extraction_llm_model") in (None, "", "mock"):
        if cases and member_id.startswith("claims"):
            return "unknown"
        if not cases:
            return "unknown"

    return "live"


def collect_individual_failures(
    member_id: str, cases: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Cases that failed while the suite summary may still pass aggregate gates."""

    out: list[dict[str, Any]] = []
    for c in cases:
        cid = c.get("case_id")
        if member_id in {"judge_pilot", "judge_holdout"}:
            if c.get("passed") is False:
                out.append(
                    {
                        "case_id": cid,
                        "passed": False,
                        "weighted_score": c.get("weighted_score"),
                        "error": c.get("error"),
                    },
                )
            continue
        metrics = c.get("metrics") if isinstance(c.get("metrics"), dict) else {}
        if metrics.get("passed") is False:
            out.append({"case_id": cid, "metrics": metrics})
    return out


def _read_validation_status(gold_path: Path) -> str | None:
    try:
        data = json.loads(gold_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    status = meta.get("validation_status")
    return str(status) if status is not None else None


def scan_validation_statuses(gold_subdir: Path | None) -> dict[str, str]:
    """Map pack directory name -> ``meta.validation_status`` for all ``gold.json`` files."""

    if gold_subdir is None or not gold_subdir.is_dir():
        return {}
    out: dict[str, str] = {}
    for path in gold_subdir.rglob("gold.json"):
        if not path.is_file():
            continue
        status = _read_validation_status(path)
        if status is None:
            continue
        out[str(path.parent.name)] = status
    return out


def summarize_validation_statuses(status_by_pack: dict[str, str]) -> str | None:
    """Majority aggregate (>=80% same) else ``mixed``."""

    if not status_by_pack:
        return None
    counts = Counter(status_by_pack.values())
    total = sum(counts.values())
    mode, cnt = counts.most_common(1)[0]
    if cnt / total >= 0.8:
        return mode
    return "mixed"


def _consistency_warnings(
    member_id: str,
    block: dict[str, Any],
    cases: list[dict[str, Any]],
    runtime_mode: RuntimeMode,
) -> list[str]:
    warnings: list[str] = []
    if block.get("error") == "missing_file" and runtime_mode != "infra_skipped":
        warnings.append(f"{member_id}: artifact missing (error=missing_file)")
    if runtime_mode == "broken_connection" and cases:
        n = sum(
            1
            for c in cases
            if str((c.get("metrics") or {}).get("request_error") or "").startswith("[Errno 111]")
        )
        warnings.append(f"{member_id}: {n}/{len(cases)} cases report connection refused")
    if runtime_mode == "canned" and cases:
        warnings.append(f"{member_id}: retrieval_trace uses mock embedding (canned / contract)")
    if runtime_mode == "mock_runtime":
        warnings.append(f"{member_id}: mock runtime answers detected")
    if runtime_mode == "synthetic_gold":
        warnings.append(f"{member_id}: hybrid ablation appears synthetic (identical MRR rows)")
    if runtime_mode == "harness_substring":
        warnings.append(f"{member_id}: harness substring fixture (not production extraction)")
    if runtime_mode == "verified_by_sibling_live":
        warnings.append(f"{member_id}: canned lane; live signal delegated to workspace_scoped_live")
    if runtime_mode == "infra_skipped":
        skip = (
            block.get("last_infra_skip") if isinstance(block.get("last_infra_skip"), dict) else {}
        )
        warnings.append(
            f"{member_id}: suite artifact missing; last infra skip: "
            f"{skip.get('artifact')} ({skip.get('reason')})",
        )
    if member_id not in _GOLD_SUBDIR_BY_MEMBER and runtime_mode == "live":
        warnings.append(f"{member_id}: unknown_member_fallback_live")
    summary = block.get("summary") if isinstance(block.get("summary"), dict) else {}
    if summary.get("all_passed") is False and member_id not in {"judge_pilot", "judge_holdout"}:
        fc = sum(1 for c in cases if (c.get("metrics") or {}).get("passed") is False)
        if fc:
            warnings.append(f"{member_id}: summary.all_passed=false with {fc} failed cases")
    return warnings


def build_trust_signal_dict(
    family_name: str,
    member_id: str,
    block: dict[str, Any],
    gold_root: Path,
) -> dict[str, Any]:
    """JSON-serializable trust_signal for one suite block under a family."""

    cases = _cases_from_block(block)
    runtime_mode = detect_runtime_mode(member_id, block, cases)
    rel = _GOLD_SUBDIR_BY_MEMBER.get(member_id)
    gold_subdir = gold_root / rel if isinstance(rel, str) else None
    status_by_pack = scan_validation_statuses(gold_subdir)
    validation_aggregate = summarize_validation_statuses(status_by_pack)
    individuals = collect_individual_failures(member_id, cases)
    is_phantom = runtime_mode in PHANTOM_RUNTIME_MODES
    warnings = _consistency_warnings(member_id, block, cases, runtime_mode)
    return {
        "family": family_name,
        "member_id": member_id,
        "runtime_mode": runtime_mode,
        "validation_status_aggregate": validation_aggregate,
        "validation_status_by_pack": status_by_pack if status_by_pack else None,
        "last_known_real_run_at": None,
        "consistency_warnings": warnings,
        "individual_failures": individuals,
        "is_phantom": is_phantom,
    }


def summarize_family_trust(family_payload: dict[str, Any], *, family_key: str) -> dict[str, Any]:
    """Roll up phantom counts across all child suite blocks (skip role, trust_aggregate)."""

    phantom_members: list[str] = []
    mixed_validation = 0
    for key, val in family_payload.items():
        if key in {"role", "trust_aggregate"} or not isinstance(val, dict):
            continue
        ts = val.get("trust_signal")
        if not isinstance(ts, dict):
            continue
        if ts.get("is_phantom"):
            phantom_members.append(f"{family_key}.{key}")
        if ts.get("validation_status_aggregate") == "mixed":
            mixed_validation += 1
    return {
        "phantom_member_count": len(phantom_members),
        "phantom_members": phantom_members,
        "mixed_validation_status_member_count": mixed_validation,
    }


def trust_baseline_payload(full_summary: dict[str, Any]) -> dict[str, Any]:
    """Minimal frozen snapshot for ``benchmark-trust-baseline.json``.

    Omits timestamps so repeated runs stay idempotent.
    """

    trust_per_family: dict[str, Any] = {}
    for fname in (
        "retrieval_family",
        "claims_family",
        "claims_production_family",
        "references_resolution_family",
        "concept_topic_family",
        "agent_tools_family",
        "chat_agent_family",
        "contradictions_family",
    ):
        block = full_summary.get(fname)
        if isinstance(block, dict):
            trust_per_family[fname] = block.get("trust_aggregate")
    dg = full_summary.get("decision_gate")
    crit = (dg or {}).get("criteria") if isinstance(dg, dict) else {}
    return {
        "schema_version": 1,
        "decision_gate": dg,
        "trust_aggregate_per_family": trust_per_family,
        "advisory_phantom_count": (crit or {}).get("advisory_phantom_count"),
        "advisory_phantom_families": (crit or {}).get("advisory_phantom_families"),
    }


def compute_gate_trust_criteria(
    *,
    retrieval_family: dict[str, Any],
    claims_family: dict[str, Any],
    claims_production_family: dict[str, Any],
    references_resolution_family: dict[str, Any],
    concept_topic_family: dict[str, Any],
    agent_tools_family: dict[str, Any],
    chat_agent_family: dict[str, Any] | None = None,
    contradictions_family: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive phantom counts, phantom member labels, and hard-block family hits."""

    phantom_labels: list[str] = []
    individual_rows: list[dict[str, Any]] = []
    hard_block: list[str] = []

    def walk(family_key: str, fam: dict[str, Any]) -> None:
        for member_id, block in fam.items():
            if member_id in {"role", "trust_aggregate"} or not isinstance(block, dict):
                continue
            ts = block.get("trust_signal")
            if not isinstance(ts, dict):
                continue
            if ts.get("is_phantom"):
                phantom_labels.append(str(member_id))
            for row in ts.get("individual_failures") or []:
                if isinstance(row, dict):
                    individual_rows.append({"family": family_key, "member_id": member_id, **row})
            if member_id in HARD_BLOCK_MEMBER_KEYS and ts.get("individual_failures"):
                label = (
                    "retrieval_judge_pilot"
                    if member_id == "judge_pilot" and family_key == "retrieval_family"
                    else f"{family_key}.{member_id}"
                )
                if label not in hard_block:
                    hard_block.append(label)

    walk("retrieval_family", retrieval_family)
    walk("claims_family", claims_family)
    walk("claims_production_family", claims_production_family)
    walk("references_resolution_family", references_resolution_family)
    walk("concept_topic_family", concept_topic_family)
    walk("agent_tools_family", agent_tools_family)
    walk("chat_agent_family", chat_agent_family or {"role": "advisory"})
    walk("contradictions_family", contradictions_family or {"role": "advisory"})

    # Future: claims_production_holdout when artifact exists
    cp_block = claims_production_family.get("claims_pilot_production")
    if isinstance(cp_block, dict):
        cp_ts = cp_block.get("trust_signal")
        if isinstance(cp_ts, dict) and cp_ts.get("individual_failures"):
            # holdout tier not wired yet; reserved
            pass

    return {
        "advisory_phantom_count": len(phantom_labels),
        "advisory_phantom_families": phantom_labels,
        "advisory_individual_failures": individual_rows,
        "hard_block_individual_failures": hard_block,
    }
