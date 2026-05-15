"""Layer-1 / layer-2 comparison table payloads for benchmark inspector."""

from __future__ import annotations

from typing import Any


def layer1_comparison_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Build metadata/authorship/reference comparison rows for layer-1 benchmark results."""

    gold = result.get("gold") or {}
    predicted = result.get("predicted") or {}
    metrics = result.get("metrics") or {}
    gold_work = gold.get("work_metadata") or {}
    pred_work = predicted.get("work_metadata") or {}
    gold_auth = gold.get("authorships") or []
    pred_auth = predicted.get("authorships") or []
    gold_refs = gold.get("references") or {}
    pred_refs = predicted.get("references") or []
    failed_checks = [
        name
        for name, passed in (metrics.get("contract", {}).get("checks") or {}).items()
        if passed is False
    ]
    metadata_rows = [
        {
            "field": field_name,
            "gold_value": gold_work.get(field_name),
            "predicted_value": pred_work.get(field_name),
        }
        for field_name in ("title", "publication_year", "doi", "arxiv_id", "work_type")
    ]
    authorship_rows = []
    max_auth = max(len(gold_auth), len(pred_auth))
    for idx in range(max_auth):
        g_item = gold_auth[idx] if idx < len(gold_auth) else {}
        p_item = pred_auth[idx] if idx < len(pred_auth) else {}
        authorship_rows.append(
            {
                "position": idx + 1,
                "gold_name": g_item.get("name"),
                "predicted_name": p_item.get("author_raw_name"),
                "gold_affiliations": g_item.get("affiliations") or [],
                "predicted_affiliations": p_item.get("raw_affiliations") or [],
            }
        )
    reference_rows = [
        {
            "field": "predicted_count",
            "gold_value": gold_refs.get("expected_count"),
            "predicted_value": len(pred_refs),
        },
        {
            "field": "sample_arxiv_ids",
            "gold_value": gold_refs.get("sample_arxiv_ids") or [],
            "predicted_value": [ref.get("arxiv_id") for ref in pred_refs if ref.get("arxiv_id")],
        },
        {
            "field": "sample_dois",
            "gold_value": gold_refs.get("sample_dois") or [],
            "predicted_value": [ref.get("doi") for ref in pred_refs if ref.get("doi")],
        },
    ]
    return {
        "metadata_rows": metadata_rows,
        "authorship_rows": authorship_rows,
        "reference_rows": reference_rows,
        "failed_checks": failed_checks,
    }


def layer2_comparison_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Build method/dataset set-diff rows for layer-2 benchmark results."""

    gold = result.get("gold") or {}
    predicted = result.get("predicted") or {}
    gold_methods = set(gold.get("expected_method_names_normalized") or [])
    gold_datasets = set(gold.get("expected_dataset_names_normalized") or [])
    pred_methods = {
        str(item.get("name", "")).strip().lower()
        for item in (predicted.get("methods") or [])
        if item.get("name")
    }
    pred_datasets = {
        str(item.get("name", "")).strip().lower()
        for item in (predicted.get("datasets") or [])
        if item.get("name")
    }
    method_rows = [
        {
            "value": name,
            "status": "match" if name in pred_methods else "miss",
            "source": "gold",
        }
        for name in sorted(gold_methods)
    ] + [
        {"value": name, "status": "extra", "source": "predicted"}
        for name in sorted(pred_methods - gold_methods)
    ]
    dataset_rows = [
        {
            "value": name,
            "status": "match" if name in pred_datasets else "miss",
            "source": "gold",
        }
        for name in sorted(gold_datasets)
    ] + [
        {"value": name, "status": "extra", "source": "predicted"}
        for name in sorted(pred_datasets - gold_datasets)
    ]
    return {"method_rows": method_rows, "dataset_rows": dataset_rows, "failed_checks": []}
