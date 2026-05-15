"""Structured compression for oversized JSON tool results (§10.9).

Used by ``tool_execution_pipeline`` as a complement to token-budget compaction.
Side-LLM calls go through ``forked_runtime.run_side_llm_chat`` (cache telemetry).
"""

from __future__ import annotations

import json
from typing import Any

from science_graphrag.agent.forked_runtime import (
    run_side_llm_chat,
    side_llm_fork_metadata,
)
from science_graphrag.agent.llm.chat import effective_chat_llm_model
from science_graphrag.config import Settings

_TOOL_USE_SUMMARY_SYSTEM = (
    "You compress one JSON tool result for downstream LLM context. "
    "Output ONE JSON object only (no markdown fences). Required keys: "
    'schema_version (string "tool_use_summary_v1"), tool (string), bullets (string array, max 12), '
    "work_ids (string array), numeric_facts (object), warnings (string array). "
    "Copy work_ids only from the input; never invent identifiers."
)


def _parse_json_object_from_llm_text(text: str) -> dict[str, Any] | None:
    s = (text or "").strip()
    if not s:
        return None
    if s.startswith("```"):
        parts = s.split("\n", 1)
        s = parts[1] if len(parts) > 1 else s
        if "```" in s:
            s = s.rsplit("```", 1)[0]
    try:
        obj = json.loads(s)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def _coerce_summary_str_list(val: Any, *, max_items: int, item_max_chars: int) -> list[str]:
    if not isinstance(val, list):
        return []
    out: list[str] = []
    for x in val[:max_items]:
        s = str(x).strip()[:item_max_chars]
        if s:
            out.append(s)
    return out


def _sanitize_llm_tool_summary_v1(parsed: dict[str, Any], tool_name: str) -> dict[str, Any]:
    """Normalize side-LLM output: stable types, caps, canonical ``tool`` name."""
    raw_nf = parsed.get("numeric_facts")
    nf: dict[str, Any] = {}
    if isinstance(raw_nf, dict):
        for k, v in list(raw_nf.items())[:24]:
            key = str(k)[:64]
            if isinstance(v, (str, int, float, bool)) or v is None:
                nf[key] = v
    warnings = _coerce_summary_str_list(parsed.get("warnings"), max_items=8, item_max_chars=240)
    bullets = _coerce_summary_str_list(parsed.get("bullets"), max_items=12, item_max_chars=800)
    work_ids = _coerce_summary_str_list(parsed.get("work_ids"), max_items=32, item_max_chars=128)
    return {
        "schema_version": "tool_use_summary_v1",
        "tool": tool_name,
        "bullets": bullets,
        "work_ids": work_ids,
        "numeric_facts": nf,
        "warnings": warnings,
    }


def _deterministic_tool_summary_v1(payload: dict[str, Any], tool_name: str) -> dict[str, Any]:
    """Cache-safe fallback when side-LLM JSON parse fails."""
    work_ids: list[str] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                lk = str(k).lower()
                if lk in {"work_id", "workid"} and isinstance(v, str) and v.strip():
                    work_ids.append(v.strip())
                walk(v)
        elif isinstance(obj, list):
            for x in obj:
                walk(x)

    walk(payload)
    uniq = list(dict.fromkeys(work_ids))[:48]
    rc = payload.get("row_count")
    bullets = [
        f"tool={tool_name}",
    ]
    if "ok" in payload:
        bullets.append(f"ok={payload.get('ok')}")
    if isinstance(rc, int):
        bullets.append(f"row_count={rc}")
    err = payload.get("error")
    if isinstance(err, str) and err.strip():
        bullets.append(f"error={err.strip()[:200]}")
    return {
        "schema_version": "tool_use_summary_v1",
        "tool": tool_name,
        "bullets": bullets[:12],
        "work_ids": uniq[:32],
        "numeric_facts": {"row_count": rc} if isinstance(rc, int) else {},
        "warnings": ["deterministic_tool_use_summary_fallback"],
    }


def canonical_tool_json_for_side_llm(
    payload: dict[str, Any],
    *,
    max_chars: int = 24000,
) -> str:
    """Serialize tool payload for side-LLM HumanMessage (Wave E2 PR1).

    Uses sorted keys and compact separators so identical logical payloads produce
    identical strings regardless of insertion order — improves prompt-cache hit
    rate for repeated ``tool_use_summary`` batches.
    """
    dumped = json.dumps(
        payload,
        ensure_ascii=True,
        default=str,
        sort_keys=True,
        separators=(",", ":"),
    )
    if len(dumped) <= max_chars:
        return dumped
    return dumped[:max_chars]


def _shrink_heavy_lists(payload: dict[str, Any], *, max_items: int = 8) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in payload.items():
        if isinstance(v, list) and len(v) > max_items:
            out[k] = v[:max_items]
            out[f"{k}_truncated_count"] = len(v) - max_items
        else:
            out[k] = v
    return out


def summarize_tool_result_payload_dict(
    *,
    settings: Settings,
    tool_name: str,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Attach structured ``_tool_use_summary`` + shrink large lists (§10.9)."""
    orig_chars = len(json.dumps(payload, ensure_ascii=True, default=str))
    fork_prompt = "Tool JSON:\n" + canonical_tool_json_for_side_llm(payload, max_chars=24000)
    fork = run_side_llm_chat(
        settings=settings,
        parent_system=_TOOL_USE_SUMMARY_SYSTEM,
        fork_prompt=fork_prompt,
        model=effective_chat_llm_model(settings),
        max_tokens=min(
            900,
            max(
                128,
                int(getattr(settings, "agent_tool_use_summary_max_output_chars", 2800) or 2800)
                // 3,
            ),
        ),
        temperature=float(getattr(settings, "agent_tool_use_summary_llm_temperature", 0.0) or 0.0),
    )
    parsed = _parse_json_object_from_llm_text(fork.text)
    summary_obj = parsed if isinstance(parsed, dict) else None
    if not summary_obj or str(summary_obj.get("schema_version") or "") != "tool_use_summary_v1":
        summary_obj = _deterministic_tool_summary_v1(payload, tool_name)
        summary_mode = "deterministic_fallback"
    else:
        summary_obj = _sanitize_llm_tool_summary_v1(summary_obj, tool_name)
        summary_mode = "llm"

    fork_meta = side_llm_fork_metadata(
        forked=fork.forked,
        side_llm_cache_read_tokens=fork.side_llm_cache_read_tokens,
        side_llm_cache_creation_tokens=fork.side_llm_cache_creation_tokens,
        side_llm_cache_read_ratio=fork.side_llm_cache_read_ratio,
    )
    merged = _shrink_heavy_lists(dict(payload), max_items=8)
    merged["_tool_use_summary"] = summary_obj
    merged["_tool_use_summary_meta"] = {
        "schema_version": "tool_use_summary_envelope_v1",
        "original_chars": orig_chars,
        "summary_mode": summary_mode,
        **fork_meta,
    }
    out_chars = len(json.dumps(merged, ensure_ascii=True, default=str))
    compression_ratio = round(orig_chars / out_chars, 4) if out_chars else None
    merged["_tool_use_summary_meta"]["merged_payload_chars"] = out_chars
    merged["_tool_use_summary_meta"]["compression_ratio_vs_original"] = compression_ratio

    meta_audit = {
        "tool": tool_name,
        "original_chars": orig_chars,
        "merged_payload_chars": out_chars,
        "compression_ratio_vs_original": compression_ratio,
        "summary_mode": summary_mode,
        **fork_meta,
    }
    max_out = int(getattr(settings, "agent_tool_use_summary_max_output_chars", 2800) or 2800)
    if out_chars > max_out:
        merged_minimal: dict[str, Any] = {
            k: merged[k]
            for k in (
                "ok",
                "error",
                "row_count",
                "empty_reason",
                "workspace_id",
                "work_id",
                "web_sources",
                "evidence_origin",
            )
            if k in merged
        }
        merged_minimal["_tool_use_summary"] = summary_obj
        merged_minimal["_tool_use_summary_meta"] = merged.get("_tool_use_summary_meta") or {}
        merged_minimal["_tool_use_summary_overflow_drop"] = True
        merged = merged_minimal
        out_chars = len(json.dumps(merged, ensure_ascii=True, default=str))
        meta_audit["merged_payload_chars_after_overflow"] = out_chars

    return merged, meta_audit


def apply_tool_use_summary_to_tool_json_content(
    *,
    settings: Settings,
    tool_name: str,
    content: str,
) -> tuple[str, dict[str, Any] | None]:
    """If enabled and payload large enough, replace JSON tool content with summarized dict."""
    if not bool(getattr(settings, "agent_tool_use_summary_enabled", False)):
        return content, None
    min_c = int(getattr(settings, "agent_tool_use_summary_min_payload_chars", 6000) or 6000)
    if len(content) < min_c:
        return content, None
    try:
        payload = json.loads(content)
    except (TypeError, ValueError, json.JSONDecodeError):
        return content, None
    if not isinstance(payload, dict):
        return content, None
    merged, meta = summarize_tool_result_payload_dict(
        settings=settings, tool_name=tool_name, payload=payload
    )
    return json.dumps(merged, ensure_ascii=False, default=str), meta


__all__ = [
    "apply_tool_use_summary_to_tool_json_content",
    "canonical_tool_json_for_side_llm",
    "summarize_tool_result_payload_dict",
]
