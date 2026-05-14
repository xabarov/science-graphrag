"""Markdown report assembly for OD workspace E2E audit."""

from __future__ import annotations

from typing import Any


def markdown_report(
    report: dict[str, Any],
    *,
    overall_ok: bool,
) -> str:
    """Human-readable summary for operators (failures, Phoenix, sequence hints)."""

    ws = report.get("workspace") or {}
    lines = [
        "# Agent OD workspace E2E audit",
        "",
        f"- **Suite:** `{report.get('suite')}`",
        f"- **Workspace:** `{ws.get('name')}` (`{ws.get('id')}`), works≈{ws.get('work_count')}",
        f"- **Overall:** {'**PASS**' if overall_ok else '**FAIL**'}",
        "",
        "## Cases",
        "",
        "| case_id | ok | steps | final_answer | answer_len | phoenix | tool_sequence | notes |",
        "|---------|----|-------|--------------|------------|---------|---------------|-------|",
    ]
    for c in report.get("cases") or []:
        cid = str(c.get("case_id") or "")
        steps = c.get("tool_steps_non_session")
        fa = bool(c.get("final_answer_reached"))
        alen = c.get("answer_len")
        ph = c.get("phoenix") or {}
        ph_ok = ph.get("ok") if isinstance(ph, dict) else None
        ok_row = (
            c.get("http_ok")
            and c.get("final_answer_reached")
            and int(c.get("answer_len") or 0) >= 40
        )
        notes = "; ".join(str(x) for x in (c.get("notes") or [])[:4])
        if c.get("error"):
            notes = (notes + "; " if notes else "") + str(c.get("error"))[:120]
        seq = " → ".join(str(x) for x in (c.get("tool_names") or [])[:18])
        if len(c.get("tool_names") or []) > 18:
            seq += " → …"
        lines.append(
            f"| {cid} | {ok_row} | {steps} | {fa} | {alen} | {ph_ok} | {seq} | {notes} |",
        )
    lines.extend(["", "## Trace / Phoenix hints (per case)", ""])
    for c in report.get("cases") or []:
        cid = str(c.get("case_id") or "")
        ta = c.get("trace_audit")
        if not isinstance(ta, dict):
            lines.append(f"### `{cid}`\n\n_(no --trace-audit)_\n")
            continue
        issues = ta.get("heuristic_issues") or []
        psa = ta.get("phoenix_structure_audit")
        lines.append(f"### `{cid}`\n")
        lines.append(f"- **Tool issues:** {issues or '—'}\n")
        if isinstance(psa, dict):
            lines.append(
                "- **Phoenix structure:** issues="
                f"{psa.get('issues') or '—'}; "
                f"llm_spans={psa.get('llm_agent_span_hits', psa.get('llm_agent_react_turn_hits'))}, "
                f"tool_spans={psa.get('tool_dot_span_hits')}, "
                f"sample_size={psa.get('span_sample_size')}\n"
            )
            sh = psa.get("sequence_hints") or []
            if sh:
                lines.append("- **Sequence / prompt hints:**\n")
                for h in sh:
                    lines.append(f"  - {h}\n")
        lines.append("")
    lines.extend(
        [
            "## JSON",
            "",
            "Machine JSON is on stdout for that run; use --write-report for JSONL artifacts.",
            "",
        ]
    )
    return "\n".join(lines)
