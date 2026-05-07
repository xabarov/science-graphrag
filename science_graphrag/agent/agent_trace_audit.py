"""Pure helpers for agent tool_trace audits (live E2E scripts, CI heuristics)."""

from __future__ import annotations

from collections import Counter
from typing import Any


def edge_search_zero_row_max_streak(trace: list[Any]) -> int:
    """Longest run of edge_search steps with row_count==0."""
    streak = 0
    max_streak = 0
    for entry in trace:
        if not isinstance(entry, dict):
            streak = 0
            continue
        if str(entry.get("tool") or "").strip() != "edge_search":
            streak = 0
            continue
        rc = entry.get("row_count")
        if not isinstance(rc, int):
            streak = 0
            continue
        if rc == 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak


def _trace_work_id(entry: dict[str, Any]) -> str | None:
    args = entry.get("args_summary")
    if not isinstance(args, dict):
        return None
    raw = args.get("work_id")
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def cypher_query_error_count(trace: list[Any]) -> int:
    """Count ``cypher_query`` steps with a non-empty ``error`` field."""

    n = 0
    for entry in trace:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("tool") or "").strip() != "cypher_query":
            continue
        err = entry.get("error")
        if err is None:
            continue
        if str(err).strip():
            n += 1
    return n


def paper_profile_max_consecutive_same_work_id(trace: list[Any]) -> int:
    """Max run length of paper_profile steps sharing the same work_id (from args_summary)."""
    streak = 0
    max_streak = 0
    current_wid: str | None = None
    for entry in trace:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("tool") or "").strip() != "paper_profile":
            streak = 0
            current_wid = None
            continue
        wid = _trace_work_id(entry)
        if not wid:
            streak = 1
            current_wid = None
            max_streak = max(max_streak, streak)
            continue
        if wid == current_wid:
            streak += 1
        else:
            streak = 1
            current_wid = wid
        max_streak = max(max_streak, streak)
    return max_streak


def build_phoenix_structure_audit(
    span_names: list[str],
    tool_trace_names: list[str],
) -> dict[str, Any]:
    """Heuristic cross-check: Phoenix span sample vs. app ``tool_trace`` (propagation / coverage).

    Uses a **flat** list of span names (from REST walk). Intended for live audits when
    ``span_names_full_cap*`` is populated; empty ``span_names`` yields a skip marker only.
    """

    sn = [str(x).strip() for x in span_names if str(x).strip()]
    flat = [str(t).strip() for t in tool_trace_names if str(t).strip()]
    non_meta = [t for t in flat if t not in ("session_init", "route_to_specialist")]

    def _is_agent_llm_span(name: str) -> bool:
        s = str(name).strip()
        return s.startswith("llm.agent.") and len(s) > len("llm.agent.")

    llm_hits = sum(1 for n in sn if _is_agent_llm_span(n))
    tool_dot = [n for n in sn if n.startswith("tool.")]
    emb = sum(1 for n in sn if "embedding.agent" in n)
    retr = sum(1 for n in sn if n.startswith("retrieval."))
    noise = sum(1 for n in sn if "ChannelWrite" in n or n.startswith("route_"))
    issues: list[str] = []
    if len(non_meta) >= 4 and llm_hits == 0 and sn:
        issues.append("phoenix_span_sample_missing_llm_agent_span")
    if len(non_meta) >= 3 and not tool_dot and sn:
        issues.append("phoenix_span_sample_missing_tool_dot_spans")
    if len(non_meta) >= 8 and llm_hits > 0 and len(tool_dot) < 2:
        issues.append("phoenix_tool_spans_sparse_vs_long_tool_trace")
    hints: list[str] = []
    ts = set(flat)
    if "edge_search" in ts and "workspace_graph_reltypes" not in ts:
        hints.append(
            "edge_search_without_workspace_graph_reltypes: model may invent rel_types; "
            "check prompts and edge_search docstring."
        )
    if flat.count("cypher_query") >= 2:
        hints.append(
            "multiple_cypher_steps: review cypher_query examples and cypher_safety alignment."
        )
    dup_tools = [t for t in set(flat) if flat.count(t) > 1 and t != "final_answer"]
    if dup_tools:
        hints.append(
            f"duplicate_tool_calls_in_trace: {sorted(dup_tools)[:8]} — check fan-out rules."
        )
    return {
        "span_sample_size": len(sn),
        "llm_agent_span_hits": llm_hits,
        "tool_dot_span_hits": len(tool_dot),
        "embedding_span_hits": emb,
        "retrieval_span_hits": retr,
        "channel_or_route_noise_hits": noise,
        "tool_dot_sample": tool_dot[:24],
        "issues": issues,
        "sequence_hints": hints,
        # Trace-review / timeline alignment (roadmap §6.3): heuristic gaps as ``missing`` list.
        "coverage": {
            "covered": len(sn),
            "missing": issues[:],
        },
    }


def _phoenix_span_names(ph: Any) -> list[str]:
    if not isinstance(ph, dict):
        return []
    full_cap = ph.get("span_names_full_cap200")
    if isinstance(full_cap, list) and full_cap:
        return [str(x) for x in full_cap]
    raw = ph.get("span_names_sample")
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return []


def _heuristic_issues_for_case(case: dict[str, Any], ctr: Counter[str]) -> list[str]:
    issues: list[str] = []
    fw = ctr.get("find_works", 0)
    if fw > 3:
        issues.append(f"high_find_works_fanout count={fw}")
    if ctr.get("idea_search", 0) + ctr.get("paper_quote_search", 0) > 4:
        issues.append("high_retrieval_churn_idea_plus_quote")
    if ctr.get("cypher_query", 0) > 2:
        issues.append("multiple_cypher_calls")
    cypher_errs = case.get("cypher_query_error_count")
    if isinstance(cypher_errs, int) and cypher_errs > 1:
        issues.append(f"cypher_query_errors count={cypher_errs}")
    esz = case.get("edge_search_zero_row_max_streak")
    if isinstance(esz, int) and esz > 1:
        issues.append(f"edge_search_consecutive_zero_rows streak={esz}")
    pp_dup = case.get("paper_profile_max_consecutive_same_work_id")
    if isinstance(pp_dup, int) and pp_dup > 1:
        issues.append(f"paper_profile_same_work_id_streak streak={pp_dup}")
    warns = case.get("warnings") or []
    if isinstance(warns, list) and warns:
        issues.append(f"api_warnings:{warns}")
    return issues


def build_tool_trace_audit(case: dict[str, Any]) -> dict[str, Any]:
    """Heuristics on tool_trace plus optional Phoenix span names (best-effort)."""
    names = case.get("tool_names") or []
    if not isinstance(names, list):
        names = []
    flat = [str(x) for x in names if x]
    ctr = Counter(flat)
    consecutive: list[str] = []
    for i in range(len(flat) - 1):
        if flat[i] == flat[i + 1] and flat[i] not in ("final_answer",):
            consecutive.append(flat[i])
    issues = _heuristic_issues_for_case(case, ctr)
    span_names = _phoenix_span_names(case.get("phoenix"))
    llm_turns = sum(1 for n in span_names if str(n).strip().startswith("llm.agent."))
    noise = sum(1 for n in span_names if "ChannelWrite" in n or n.startswith("route_"))
    tool_like = sum(1 for n in span_names if n.startswith("tool."))
    out: dict[str, Any] = {
        "tool_counts": dict(sorted(ctr.items(), key=lambda kv: (-kv[1], kv[0]))),
        "consecutive_duplicate_tools": consecutive,
        "tools_called_more_than_once": {k: v for k, v in ctr.items() if v > 1},
        "phoenix_sample_llm_agent_span_hits": llm_turns,
        "phoenix_sample_channel_or_route_hits": noise,
        "phoenix_sample_tool_dot_hits": tool_like,
        "heuristic_issues": issues,
    }
    if span_names:
        out["phoenix_structure_audit"] = build_phoenix_structure_audit(span_names, flat)
    return out
