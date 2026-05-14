"""JSON/markdown helpers for trace-review artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def patch_run_context_execution_diagnostics(
    doc: dict[str, Any],
    *,
    exec_stages: list[dict[str, Any]],
    hb_sec: float,
    e2e_subprocess_timeout_sec: float | None,
) -> None:
    """Refresh ``run_context.execution_diagnostics`` after late stages (e.g. compaction)."""
    rc = doc.get("run_context")
    if not isinstance(rc, dict):
        return
    rc2 = dict(rc)
    rc2["execution_diagnostics"] = {
        "heartbeat_interval_sec": hb_sec,
        "e2e_subprocess_timeout_sec": e2e_subprocess_timeout_sec,
        "stages": list(exec_stages),
    }
    doc["run_context"] = rc2


def json_safe_value(value: Any) -> Any:
    """Recursively coerce values into JSON-serializable primitives."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(k): json_safe_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe_value(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe_value(v) for v in value]
    return value


def checks_dict(checks: list[dict[str, Any]]) -> dict[str, bool]:
    return {str(c.get("name")): bool(c.get("ok")) for c in checks if c.get("name")}


def sse_missing_final(checks: list[dict[str, Any]]) -> bool:
    for c in checks:
        if c.get("name") == "agent_v2_sse" and "missing_final_answer" in str(c.get("detail") or ""):
            return True
    return False


def server_agent_runtime_from_checks(checks: list[dict[str, Any]]) -> str | None:
    """Prefer API-reported ``run_metadata.agent_runtime`` when client env omits it."""
    for c in checks:
        if str(c.get("name") or "") != "agent_v2_sync_json" or not c.get("ok"):
            continue
        data = c.get("data") if isinstance(c.get("data"), dict) else {}
        rm = data.get("run_metadata") if isinstance(data.get("run_metadata"), dict) else {}
        rt = str(rm.get("agent_runtime") or "").strip()
        return rt or None
    return None


def write_markdown(path: Path, review_dict: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Agent Trace Review")
    lines.append("")
    lines.append(f"- Generated: `{review_dict.get('generated_at')}`")
    ctx = review_dict.get("run_context") or {}
    lines.append(f"- Base URL: `{ctx.get('base_url')}`")
    lines.append(f"- Workspace: `{ctx.get('workspace_id')}`")
    lines.append(f"- Suite: `{ctx.get('suite')}`")
    if ctx.get("run_kind"):
        lines.append(f"- Run kind: `{ctx.get('run_kind')}`")
    if ctx.get("graph_id"):
        lines.append(f"- Graph id: `{ctx.get('graph_id')}`")
    if review_dict.get("phoenix_snapshot_path"):
        lines.append(f"- Phoenix snapshot: `{review_dict.get('phoenix_snapshot_path')}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| Check | OK | Detail |")
    lines.append("|------|----|--------|")
    for chk in review_dict.get("checks") or []:
        if not isinstance(chk, dict):
            continue
        det = str(chk.get("detail") or "")[:180]
        lines.append(f"| `{chk.get('name')}` | `{bool(chk.get('ok'))}` | {det} |")
    lines.append("")

    tl = review_dict.get("trace_timeline") or []
    if tl:
        lines.append("## Trace timeline")
        lines.append("")
        lines.append(
            "| Case | Run kind | Graph id | Steps | last_tool | "
            "Phoenix missing | dur_ms | warnings |",
        )
        lines.append(
            "|------|----------|----------|-------|-----------|"
            "-----------------|--------|----------|",
        )
        for row in tl:
            steps = row.get("tool_steps") or []
            last_tool = steps[-1].get("tool") if steps else ""
            pa = row.get("phoenix_alignment") or {}
            miss_n = len(pa.get("missing") or []) if isinstance(pa, dict) else 0
            warns = row.get("warnings") or []
            wshort = ",".join(str(x)[:40] for x in warns[:2])
            lines.append(
                f"| `{row.get('case_id')}` | `{row.get('run_kind')}` | `{row.get('graph_id')}` "
                f"| {len(steps)} | `{last_tool}` | {miss_n} | "
                f"`{row.get('duration_ms')}` | {wshort[:80]} |",
            )
        lines.append("")

    lines.append("## Metrics")
    lines.append("")
    m = review_dict.get("metrics") or {}
    for k in sorted(m.keys()):
        lines.append(f"- `{k}`: `{m.get(k)}`")
    lines.append("")

    e2e = review_dict.get("e2e_audit")
    if isinstance(e2e, dict):
        lines.append("## E2E Audit")
        lines.append("")
        lines.append(f"- OK: `{bool(e2e.get('ok'))}`")
        lines.append(f"- Return code: `{e2e.get('returncode')}`")
        lines.append(f"- Report path: `{e2e.get('report_path')}`")
        if e2e.get("full_report_json_path"):
            lines.append(f"- Full JSON: `{e2e.get('full_report_json_path')}`")
        lines.append("")

    ph = review_dict.get("phoenix_pull")
    if isinstance(ph, dict) and not ph.get("skipped"):
        lines.append("## Phoenix pull")
        lines.append("")
        lines.append(f"- OK: `{ph.get('ok')}`")
        lines.append(f"- Path: `{ph.get('path')}`")
        lines.append("")

    cre = review_dict.get("compaction_turn_review")
    if isinstance(cre, dict):
        lines.append("## Compaction turn review")
        lines.append("")
        lines.append(f"- OK: `{cre.get('ok')}`")
        lines.append(f"- Path: `{cre.get('path')}`")
        lines.append("")

    verdict = review_dict.get("verdict") or {}
    lines.append("## Verdict")
    lines.append("")
    lines.append(f"- Status: `{verdict.get('status')}`")
    for reason in verdict.get("fail_reasons") or []:
        lines.append(f"- FAIL: {reason}")
    for reason in verdict.get("warn_reasons") or []:
        lines.append(f"- WARN: {reason}")

    acc = review_dict.get("acceptance_summary")
    if isinstance(acc, dict):
        lines.append("")
        lines.append("## Acceptance summary (§10.10)")
        lines.append("")
        lines.append(f"- schema: `{acc.get('schema_version')}`")
        gates = acc.get("gates") if isinstance(acc.get("gates"), dict) else {}
        for gk, gv in sorted(gates.items()):
            lines.append(f"- `{gk}`: `{gv}`")
        sc = acc.get("synthetic_covered") or []
        if isinstance(sc, list) and sc:
            lines.append("")
            lines.append("### synthetic_covered")
            for item in sc[:30]:
                lines.append(f"- {item}")
            if len(sc) > 30:
                lines.append(f"- … ({len(sc) - 30} more)")
        lp = acc.get("live_proven") or []
        if isinstance(lp, list) and lp:
            lines.append("")
            lines.append("### live_proven")
            for item in lp:
                lines.append(f"- {item}")
        ro = acc.get("residual_open") or []
        if isinstance(ro, list) and ro:
            lines.append("")
            lines.append("### residual_open")
            for item in ro:
                lines.append(f"- {item}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
