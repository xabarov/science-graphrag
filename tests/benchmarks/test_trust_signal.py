"""Unit tests for BT1 trust_signal and decision_gate overlays."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from science_graphrag.benchmarks.decision_gate import evaluate_decision_gate
from science_graphrag.benchmarks.trust_signal import (
    _consistency_warnings,
    build_trust_signal_dict,
    collect_individual_failures,
    compute_gate_trust_criteria,
    detect_runtime_mode,
    scan_validation_statuses,
    summarize_validation_statuses,
    trust_baseline_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLD_ROOT = REPO_ROOT / "tests" / "fixtures" / "benchmarks"

_PARAPHRASE_OK = {
    "all_passed": True,
    "summary": {"all_passed": True},
    "cases": [
        {
            "case_id": "stub_core_ok",
            "metrics": {
                "passed": True,
                "claim_recall": 0.75,
                "claim_precision": 0.72,
            },
        },
    ],
}


def test_detect_runtime_mode_workspace_canned() -> None:
    cases = [
        {"case_id": "a", "retrieval_trace": {"embedding": {"embedding_model": "mock"}}},
    ]
    block: dict = {"run_metadata": {"extraction_llm_model": "x"}}
    assert detect_runtime_mode("workspace_scoped", block, cases) == "canned"


def test_detect_runtime_mode_workspace_live() -> None:
    cases = [
        {"case_id": "a", "retrieval_trace": {"embedding": {"embedding_model": "baai/bge-m3"}}},
    ]
    block: dict = {"run_metadata": {"extraction_llm_model": "x"}}
    assert detect_runtime_mode("workspace_scoped", block, cases) == "live"


def test_detect_runtime_mode_agent_mock() -> None:
    cases = [{"case_id": "1", "answer": "mock answer", "citations": []}]
    block: dict = {"run_metadata": {"extraction_llm_model": "x"}}
    assert detect_runtime_mode("agent_tools_mini", block, cases) == "mock_runtime"


def test_detect_runtime_mode_agent_tools_multiagent_benchmark_stub() -> None:
    cases = [
        {
            "case_id": "m1",
            "answer": "benchmark_stub_answer:m1",
            "citations": [{"work_id": "benchmark-stub-work:m1"}],
        },
    ]
    block: dict = {"run_metadata": {"extraction_llm_model": "x"}}
    assert detect_runtime_mode("agent_tools_multiagent", block, cases) == "live"


def test_detect_runtime_mode_contradictions_v1_mini_live() -> None:
    cases = [{"case_id": "pair_01", "metrics": {"passed": True}}]
    block: dict = {"run_metadata": {}}
    assert detect_runtime_mode("contradictions_v1_mini", block, cases) == "live"


def test_detect_runtime_mode_multihop_broken() -> None:
    cases = [
        {
            "case_id": "m1",
            "metrics": {"request_error": "[Errno 111] Connection refused"},
        },
    ]
    block: dict = {"run_metadata": {}}
    assert detect_runtime_mode("multihop_mini", block, cases) == "broken_connection"


def test_detect_runtime_mode_multihop_infra_skipped() -> None:
    block: dict = {
        "error": "missing_file",
        "last_infra_skip": {"artifact": "eval/results/multihop-skipped-test.json"},
    }
    assert detect_runtime_mode("multihop_mini", block, []) == "infra_skipped"


def test_detect_runtime_mode_claims_paraphrase_oracle_synthetic() -> None:
    cases = [
        {"case_id": "c1", "oracle_predictions": True, "metrics": {"passed": True}},
        {"case_id": "c2", "oracle_predictions": True, "metrics": {"passed": True}},
    ]
    block: dict = {"run_metadata": {}}
    assert detect_runtime_mode("claims_paraphrase_pilot", block, cases) == "synthetic_gold"


def test_detect_runtime_mode_claims_paraphrase_explicit_live() -> None:
    cases = [
        {"case_id": "c1", "runtime_mode": "live", "oracle_predictions": False},
        {"case_id": "c2", "runtime_mode": "live", "oracle_predictions": False},
    ]
    block: dict = {"run_metadata": {}}
    assert detect_runtime_mode("claims_paraphrase_holdout", block, cases) == "live"


def test_detect_runtime_mode_workspace_verified_by_sibling_live() -> None:
    cases = [
        {"case_id": "a", "retrieval_trace": {"embedding": {"embedding_model": "mock"}}},
    ]
    block: dict = {
        "_workspace_scoped_delegated_to_live": True,
        "run_metadata": {"extraction_llm_model": "x"},
    }
    assert detect_runtime_mode("workspace_scoped", block, cases) == "verified_by_sibling_live"


def test_build_trust_signal_multihop_infra_skipped_not_phantom() -> None:
    block = {
        "artifact": "eval/results/current-retrieval-multihop-mini.json",
        "error": "missing_file",
        "summary": {},
        "cases": [],
        "last_infra_skip": {"artifact": "eval/results/multihop-skipped-x.json", "reason": "x"},
    }
    ts = build_trust_signal_dict("retrieval_family", "multihop_mini", block, GOLD_ROOT)
    assert ts["runtime_mode"] == "infra_skipped"
    assert ts["is_phantom"] is False


def test_detect_runtime_mode_v3_judge_mock() -> None:
    block: dict = {"run_metadata": {"mock_agent": True}}
    assert detect_runtime_mode("v3_judge_mini", block, []) == "mock_runtime"


def test_detect_runtime_mode_v3_judge_live() -> None:
    block: dict = {"run_metadata": {"mock_agent": False}}
    assert (
        detect_runtime_mode("v3_judge_pilot", block, [{"case_id": "x", "passed": True}]) == "live"
    )


def test_collect_individual_failures_v3_judge_branch() -> None:
    cases = [{"case_id": "a", "passed": False, "weighted_score": 1.0}]
    out = collect_individual_failures("v3_judge_pilot", cases)
    assert len(out) == 1


def test_judge_holdout_artifact_has_per_case_score_breakdown() -> None:
    p = REPO_ROOT / "eval/results/current-retrieval-judge-holdout.json"
    if not p.is_file():
        return
    data = json.loads(p.read_text(encoding="utf-8"))
    br = (data.get("summary") or {}).get("per_case_score_breakdown")
    assert isinstance(br, list) and br
    assert all("case_id" in row and "weighted_score" in row for row in br)


def test_detect_runtime_mode_hybrid_synthetic() -> None:
    cases = [
        {"case_id": "h1", "metrics": {"mrr_vector": 0.5, "mrr_hybrid": 1.0, "mrr_delta": 0.5}},
        {"case_id": "h2", "metrics": {"mrr_vector": 0.5, "mrr_hybrid": 1.0, "mrr_delta": 0.5}},
    ]
    block: dict = {"run_metadata": {"extraction_llm_model": None}}
    assert detect_runtime_mode("hybrid_ablation", block, cases) == "synthetic_gold"


def test_detect_runtime_mode_hybrid_ablation_live_hit_only_contract_verified() -> None:
    """BT4: hybrid live artifact may be hit-only (no MRR triples) until runner emits BT4 metrics."""
    cases = [
        {"case_id": "ha_anchor_free", "metrics": {"passed": True, "hit_count": 5, "hit_ok": True}},
    ]
    block: dict = {"run_metadata": {"extraction_llm_model": "mistralai/x"}}
    assert detect_runtime_mode("hybrid_ablation_live", block, cases) == "contract_verified"


def test_cross_ref_validation_status_majority(tmp_path: Path) -> None:
    root = tmp_path / "claims"
    for i, status in enumerate(
        ["llm_dual_validated"] * 4 + ["draft"],
        start=1,
    ):
        d = root / f"pack_{i}"
        d.mkdir(parents=True)
        (d / "gold.json").write_text(
            json.dumps({"meta": {"validation_status": status}}),
            encoding="utf-8",
        )
    by_pack = scan_validation_statuses(root)
    assert summarize_validation_statuses(by_pack) == "llm_dual_validated"


def test_cross_ref_validation_status_mixed(tmp_path: Path) -> None:
    root = tmp_path / "claims"
    specs = [
        ("a", "llm_dual_validated"),
        ("b", "llm_dual_validated"),
        ("c", "draft"),
        ("d", "draft"),
        ("e", "llm_triple_validated"),
    ]
    for name, status in specs:
        d = root / name
        d.mkdir(parents=True)
        (d / "gold.json").write_text(
            json.dumps({"meta": {"validation_status": status}}),
            encoding="utf-8",
        )
    assert summarize_validation_statuses(scan_validation_statuses(root)) == "mixed"


def test_decision_gate_phantom_downgrades_go_to_conditional() -> None:
    reference = {"all_passed": True}
    layer1 = {"failed_count": 0}
    layer2 = {"failed_count": 0}
    claims_prod = {"all_passed": True, "mean_claim_recall": 0.9}
    trust = {
        "advisory_phantom_count": 3,
        "advisory_phantom_families": ["a", "b", "c"],
        "advisory_individual_failures": [],
        "hard_block_individual_failures": [],
    }
    dg = evaluate_decision_gate(
        reference,
        layer1,
        layer2,
        claims_prod,
        claims_paraphrase_pilot=_PARAPHRASE_OK,
        claims_paraphrase_holdout=_PARAPHRASE_OK,
        trust_criteria=trust,
    )
    assert dg["decision"] == "CONDITIONAL-GO"
    assert "advisory_phantom_count=3" in dg["reason"]


def test_decision_gate_hard_block_individual_failures_no_go() -> None:
    reference = {"all_passed": True}
    layer1 = {"failed_count": 0}
    layer2 = {"failed_count": 0}
    claims_prod = {"all_passed": True, "mean_claim_recall": 0.9}
    trust = {
        "advisory_phantom_count": 0,
        "advisory_phantom_families": [],
        "advisory_individual_failures": [
            {"family": "retrieval_family", "member_id": "judge_pilot", "case_id": "x"},
        ],
        "hard_block_individual_failures": ["retrieval_judge_pilot"],
    }
    dg = evaluate_decision_gate(
        reference,
        layer1,
        layer2,
        claims_prod,
        claims_paraphrase_pilot=_PARAPHRASE_OK,
        claims_paraphrase_holdout=_PARAPHRASE_OK,
        trust_criteria=trust,
    )
    assert dg["decision"] == "NO-GO"
    assert "hard_block_individual_failures" in dg["reason"]


def test_decision_gate_clean_state_still_go() -> None:
    reference = {"all_passed": True}
    layer1 = {"failed_count": 0}
    layer2 = {"failed_count": 0}
    claims_prod = {"all_passed": True, "mean_claim_recall": 0.9}
    trust = {
        "advisory_phantom_count": 0,
        "advisory_phantom_families": [],
        "advisory_individual_failures": [],
        "hard_block_individual_failures": [],
    }
    dg = evaluate_decision_gate(
        reference,
        layer1,
        layer2,
        claims_prod,
        claims_paraphrase_pilot=_PARAPHRASE_OK,
        claims_paraphrase_holdout=_PARAPHRASE_OK,
        trust_criteria=trust,
    )
    assert dg["decision"] == "GO"


def test_decision_gate_paraphrase_below_bt6_core_bar_is_no_go() -> None:
    reference = {"all_passed": True}
    layer1 = {"failed_count": 0}
    layer2 = {"failed_count": 0}
    claims_prod = {"all_passed": True, "mean_claim_recall": 1.0}
    weak = {
        "all_passed": True,
        "summary": {"all_passed": True},
        "cases": [
            {
                "case_id": "weak",
                "metrics": {"passed": True, "claim_recall": 0.8, "claim_precision": 0.2},
            },
        ],
    }
    trust = {
        "advisory_phantom_count": 0,
        "advisory_phantom_families": [],
        "advisory_individual_failures": [],
        "hard_block_individual_failures": [],
    }
    dg = evaluate_decision_gate(
        reference,
        layer1,
        layer2,
        claims_prod,
        claims_paraphrase_pilot=weak,
        claims_paraphrase_holdout=_PARAPHRASE_OK,
        trust_criteria=trust,
    )
    assert dg["decision"] == "NO-GO"
    assert "claims_paraphrase_core_bar_not_met" in dg["reason"]
    assert dg["criteria"]["claims_paraphrase_pilot_meets_bt6_core_bar"] is False


def test_decision_gate_two_design_phantoms_still_go() -> None:
    """merge_safe_contract_mock + strict_pilot_mock are expected canned lanes (Wave 6)."""
    reference = {"all_passed": True}
    layer1 = {"failed_count": 0}
    layer2 = {"failed_count": 0}
    claims_prod = {"all_passed": True, "mean_claim_recall": 0.9}
    trust = {
        "advisory_phantom_count": 2,
        "advisory_phantom_families": ["merge_safe_contract_mock", "strict_pilot_mock"],
        "advisory_individual_failures": [],
        "hard_block_individual_failures": [],
    }
    dg = evaluate_decision_gate(
        reference,
        layer1,
        layer2,
        claims_prod,
        claims_paraphrase_pilot=_PARAPHRASE_OK,
        claims_paraphrase_holdout=_PARAPHRASE_OK,
        trust_criteria=trust,
    )
    assert dg["decision"] == "GO"


def test_build_trust_signal_judge_collects_failures() -> None:
    block = {
        "artifact": "x.json",
        "run_metadata": {},
        "summary": {"all_passed": False},
        "cases": [
            {"case_id": "ok", "passed": True, "weighted_score": 6.0},
            {"case_id": "bad", "passed": False, "weighted_score": 2.0},
        ],
    }
    ts = build_trust_signal_dict("retrieval_family", "judge_pilot", block, GOLD_ROOT)
    assert ts["runtime_mode"] == "live"
    assert len(ts["individual_failures"]) == 1
    assert ts["individual_failures"][0]["case_id"] == "bad"


def test_collect_individual_failures_judge_branch() -> None:
    cases = [{"case_id": "a", "passed": False, "weighted_score": 1.0}]
    out = collect_individual_failures("judge_pilot", cases)
    assert len(out) == 1


def test_aggregator_smoke_runs(tmp_path: Path) -> None:
    """Smoke: aggregate script exits 0 against copied minimal eval dir (optional)."""

    script = REPO_ROOT / "scripts" / "aggregate_benchmark_metrics.py"
    out_json = tmp_path / "summary.json"
    out_md = tmp_path / "summary.md"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert "decision_gate" in data
    assert "agent_v3_quality_family" in data
    assert "trust_signal" in data["retrieval_family"]["workspace_scoped"]


def test_baseline_snapshot_idempotent() -> None:
    payload = {
        "decision_gate": {
            "decision": "CONDITIONAL-GO",
            "reason": "x",
            "criteria": {"advisory_phantom_count": 2, "advisory_phantom_families": ["a", "b"]},
        },
        "retrieval_family": {"trust_aggregate": {"phantom_member_count": 2}},
        "claims_family": {"trust_aggregate": {}},
        "claims_production_family": {"trust_aggregate": {}},
        "references_resolution_family": {"trust_aggregate": {}},
        "concept_topic_family": {"trust_aggregate": {}},
        "agent_tools_family": {"trust_aggregate": {}},
        "agent_v3_quality_family": {"trust_aggregate": {}},
    }
    a = json.dumps(trust_baseline_payload(payload), sort_keys=True, ensure_ascii=False)
    b = json.dumps(trust_baseline_payload(payload), sort_keys=True, ensure_ascii=False)
    assert a == b


def test_trust_baseline_payload_replaces_advisory_rows_with_count() -> None:
    payload = {
        "decision_gate": {
            "decision": "GO",
            "reason": "all_nightly_passed",
            "criteria": {
                "advisory_phantom_count": 0,
                "advisory_individual_failures": [{"case_id": "c1"}, {"case_id": "c2"}],
            },
        },
        "retrieval_family": {"trust_aggregate": {}},
        "claims_family": {"trust_aggregate": {}},
        "claims_production_family": {"trust_aggregate": {}},
        "references_resolution_family": {"trust_aggregate": {}},
        "concept_topic_family": {"trust_aggregate": {}},
        "agent_tools_family": {"trust_aggregate": {}},
        "agent_v3_quality_family": {"trust_aggregate": {}},
    }
    slim = trust_baseline_payload(payload)
    crit = (slim.get("decision_gate") or {}).get("criteria") or {}
    assert "advisory_individual_failures" not in crit
    assert crit.get("advisory_individual_failure_count") == 2


def test_chat_agent_contract_runtime_mode() -> None:
    mode = detect_runtime_mode(
        "chat_agent_contract",
        {"run_metadata": {}},
        [{"case_id": "x", "metrics": {"passed": True}}],
    )
    assert mode == "contract_verified"


def test_unknown_member_fallbacks_to_live_with_warning() -> None:
    """Unknown member_id falls back to live and emits unknown_member_fallback_live warning."""
    block: dict = {"run_metadata": {"extraction_llm_model": "some-model"}}
    cases = [{"case_id": "x", "metrics": {"passed": True}}]
    mode = detect_runtime_mode("totally_new_member_xyz", block, cases)
    assert mode == "live"
    warns = _consistency_warnings("totally_new_member_xyz", block, cases, mode)
    assert any("unknown_member_fallback_live" in w for w in warns)


def test_compute_gate_trust_criteria_wires_judge_hard_block() -> None:
    retrieval = {
        "role": "advisory",
        "judge_pilot": {
            "trust_signal": {
                "is_phantom": False,
                "individual_failures": [{"case_id": "x", "passed": False}],
            },
        },
    }
    empty = {"role": "advisory"}
    crit = compute_gate_trust_criteria(
        retrieval_family=retrieval,
        claims_family=empty,
        claims_production_family={"role": "core"},
        references_resolution_family=empty,
        concept_topic_family=empty,
        agent_tools_family=empty,
        agent_v3_quality_family={"role": "advisory"},
        chat_agent_family=empty,
        contradictions_family=empty,
    )
    assert "retrieval_judge_pilot" in crit["hard_block_individual_failures"]
