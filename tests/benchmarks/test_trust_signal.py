"""Unit tests for BT1 trust_signal and decision_gate overlays."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from science_graphrag.benchmarks.decision_gate import evaluate_decision_gate
from science_graphrag.benchmarks.trust_signal import (
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


def test_judge_holdout_artifact_has_per_case_score_breakdown() -> None:
    p = REPO_ROOT / "eval/results/current-retrieval-judge-holdout.json"
    if not p.is_file():
        return
    data = json.loads(p.read_text(encoding="utf-8"))
    br = (data.get("summary") or {}).get("per_case_score_breakdown")
    assert isinstance(br, list) and br
    assert all("case_id" in row and "weighted" in row for row in br)


def test_detect_runtime_mode_hybrid_synthetic() -> None:
    cases = [
        {"case_id": "h1", "metrics": {"mrr_vector": 0.5, "mrr_hybrid": 1.0, "mrr_delta": 0.5}},
        {"case_id": "h2", "metrics": {"mrr_vector": 0.5, "mrr_hybrid": 1.0, "mrr_delta": 0.5}},
    ]
    block: dict = {"run_metadata": {"extraction_llm_model": None}}
    assert detect_runtime_mode("hybrid_ablation", block, cases) == "synthetic_gold"


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
    assert "trust_signal" in data["retrieval_family"]["workspace_scoped"]


def test_baseline_snapshot_idempotent(tmp_path: Path) -> None:
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
    }
    a = json.dumps(trust_baseline_payload(payload), sort_keys=True, ensure_ascii=False)
    b = json.dumps(trust_baseline_payload(payload), sort_keys=True, ensure_ascii=False)
    assert a == b


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
    )
    assert "retrieval_judge_pilot" in crit["hard_block_individual_failures"]
