#!/usr/bin/env python3
"""Operator closeout runner for external-research live/Phoenix verification."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from external_research_closeout_validate import (  # noqa: E402  # pylint: disable=import-error
    gate_status,
    lane_issue_list,
    markdown_for_lane_report,
    tool_names_from_trace,
)
from external_web_research_validate import (  # noqa: E402  # pylint: disable=import-error
    evaluate_external_web_research_case,
)
from http_suite_core import _extra_headers  # noqa: E402  # pylint: disable=import-error

_DEFAULT_BASE = "http://127.0.0.1:18787"
_DEFAULT_WORKSPACE = "ws-pilot-od"
_DEFAULT_TIMEOUT = 180.0
_DEFAULT_REPORT_DIR_PREFIX = "external-research-closeout-"
_DEFAULT_EXTERNAL_QUESTION = (
    "поищи в интернете о YOLO v 11 и приведи официальные источники и факты релиза"
)
_DEFAULT_ARXIV_QUESTION = (
    "Найди arXiv-публикацию Attention Is All You Need и кратко опиши по аннотации."
)
_DEFAULT_UNPAYWALL_QUESTION = (
    "Проверь OA-доступ через Unpaywall для DOI 10.48550/arXiv.1706.03762."
)
_DEFAULT_OPENALEX_QUESTION = "Подбери релевантные работы по object detection за последние годы."
_DEFAULT_S2_QUESTION = "Найди в Semantic Scholar статью Attention Is All You Need и верни карточку."
_DEFAULT_PDF_URL = "https://arxiv.org/pdf/1706.03762.pdf"


def _run_pytest(paths: list[str]) -> tuple[bool, str]:
    cmd = [str(_REPO_ROOT / ".venv/bin/pytest"), *paths, "-q"]
    proc = subprocess.run(  # noqa: S603
        cmd,
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    tail = "\n".join((proc.stdout + "\n" + proc.stderr).strip().splitlines()[-20:])
    return proc.returncode == 0, tail


def _pull_phoenix_trace(
    *,
    trace_id: str,
    out_jsonl: Path,
    base_url: str | None,
    timeout: float,
) -> dict[str, Any]:
    if not trace_id.strip():
        return {"fetch_ok": False, "error": "missing_trace_id", "span_count": 0}
    cmd = [
        str(_REPO_ROOT / ".venv/bin/python"),
        str(_SCRIPT_DIR / "phoenix_trace_pull.py"),
        "--trace-id",
        trace_id.strip(),
        "--out-jsonl",
        str(out_jsonl),
        "--timeout",
        str(timeout),
    ]
    if base_url:
        cmd.extend(["--base-url", base_url])
    proc = subprocess.run(  # noqa: S603
        cmd,
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if not out_jsonl.exists():
        return {"fetch_ok": False, "error": "phoenix_output_missing", "span_count": 0}
    try:
        row = json.loads(out_jsonl.read_text(encoding="utf-8").splitlines()[0])
    except (ValueError, IndexError):
        return {"fetch_ok": False, "error": "phoenix_output_parse_error", "span_count": 0}
    row["command_ok"] = proc.returncode == 0
    row["stderr_tail"] = "\n".join(proc.stderr.strip().splitlines()[-10:])
    return row


def _post_agent_query(
    *,
    base_url: str,
    timeout: float,
    payload: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{base_url.rstrip('/')}/v2/agent/query",
                json=payload,
                headers={"Accept": "application/json", **_extra_headers()},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        return False, {"error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(data, dict):
        return False, {"error": "invalid_json_body"}
    return True, data


def _settings_source_test(
    *,
    base_url: str,
    timeout: float,
    source_id: str,
) -> tuple[bool, dict[str, Any]]:
    payload = {"source_id": source_id}
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{base_url.rstrip('/')}/v1/settings/agent_tools/test_source",
                json=payload,
                headers={"Accept": "application/json", **_extra_headers()},
            )
            resp.raise_for_status()
            body = resp.json()
    except Exception as exc:  # noqa: BLE001
        return False, {"error": f"{type(exc).__name__}: {exc}"}
    return bool(body.get("ok") is True), body if isinstance(body, dict) else {}


def _run_command(command: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(  # noqa: S603
        command,
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    text = (proc.stdout + "\n" + proc.stderr).strip()
    return proc.returncode == 0, text


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("AGENT_LIVE_BASE", _DEFAULT_BASE))
    parser.add_argument(
        "--workspace-id",
        default=(os.getenv("AGENT_LIVE_WORKSPACE_ID") or _DEFAULT_WORKSPACE).strip(),
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory under eval/results (default auto timestamped)",
    )
    parser.add_argument("--timeout", type=float, default=_DEFAULT_TIMEOUT)
    parser.add_argument(
        "--phoenix-base-url",
        default=(os.getenv("PHOENIX_UI_BASE_URL") or "").strip(),
        help="Optional Phoenix UI base URL for trace pull",
    )
    parser.add_argument("--skip-live", action="store_true")
    parser.add_argument("--skip-unit", action="store_true")
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_dir = (
        Path(args.out_dir)
        if args.out_dir.strip()
        else (_REPO_ROOT / "eval/results" / f"{_DEFAULT_REPORT_DIR_PREFIX}{stamp}")
    )
    out_dir = out_dir if out_dir.is_absolute() else (_REPO_ROOT / out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    root_report: dict[str, Any] = {
        "base_url": args.base_url.rstrip("/"),
        "workspace_id": args.workspace_id,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "unit_checks": [],
        "lanes": {},
    }

    if not args.skip_unit:
        checks = [
            "tests/scripts/live_check/test_external_web_research_validate.py",
            "tests/scripts/live_check/test_mcp_agent_e2e_validate.py",
            "tests/agent/test_semantic_scholar_tools.py",
            "tests/agent/test_openalex_works_search_tools.py",
        ]
        ok, tail = _run_pytest(checks)
        unit_row = {"ok": ok, "checks": checks, "tail": tail}
        root_report["unit_checks"].append(unit_row)
        _write_json(out_dir / "unit-contract-checks.json", unit_row)

    if args.skip_live:
        root_report["live_skipped"] = True
        _write_json(out_dir / "index.json", root_report)
        _write_text(out_dir / "index.md", "# External research closeout\n\n- live lanes skipped.\n")
        return 0

    lane_specs = [
        {
            "lane_id": "external_web",
            "payload": {
                "question": _DEFAULT_EXTERNAL_QUESTION,
                "workspace_id": args.workspace_id,
                "web_research_enabled": True,
            },
            "expected_tools": ("official_web_lookup", "web_fetch"),
            "source_test_id": "openalex",
        },
        {
            "lane_id": "arxiv",
            "payload": {
                "question": _DEFAULT_ARXIV_QUESTION,
                "workspace_id": args.workspace_id,
                "web_research_enabled": True,
            },
            "expected_tools": ("arxiv_search",),
            "source_test_id": "openalex",
        },
        {
            "lane_id": "unpaywall",
            "payload": {
                "question": _DEFAULT_UNPAYWALL_QUESTION,
                "workspace_id": args.workspace_id,
                "web_research_enabled": True,
            },
            "expected_tools": ("unpaywall_lookup",),
            "source_test_id": "openalex",
        },
        {
            "lane_id": "openalex",
            "payload": {
                "question": _DEFAULT_OPENALEX_QUESTION,
                "workspace_id": args.workspace_id,
                "web_research_enabled": True,
            },
            "expected_tools": ("openalex_works_search",),
            "source_test_id": "openalex",
        },
        {
            "lane_id": "semantic_scholar",
            "payload": {
                "question": _DEFAULT_S2_QUESTION,
                "workspace_id": args.workspace_id,
                "web_research_enabled": True,
            },
            "expected_tools": ("semantic_scholar_search",),
            "source_test_id": "semantic_scholar",
        },
        {
            "lane_id": "pdf_read",
            "payload": {
                "question": "__sg_pdf_read_action__",
                "workspace_id": args.workspace_id,
                "web_research_enabled": True,
                "pdf_read_request": {"pdf_url": _DEFAULT_PDF_URL},
            },
            "expected_tools": ("read_external_pdf",),
            "source_test_id": "openalex",
        },
    ]

    lane_rows: list[dict[str, Any]] = []
    for spec in lane_specs:
        lane_id = str(spec["lane_id"])
        expected_tools = tuple(spec["expected_tools"])
        payload = dict(spec["payload"])

        http_ok, data = _post_agent_query(
            base_url=args.base_url,
            timeout=args.timeout,
            payload=payload,
        )
        trace_id = str(data.get("phoenix_trace_id") or "") if http_ok else ""
        smoke_json = out_dir / f"{lane_id}-smoke.json"
        _write_json(
            smoke_json,
            {
                "lane_id": lane_id,
                "http_ok": http_ok,
                "request_payload_digest": payload,
                "response": data,
            },
        )

        phoenix_jsonl = out_dir / f"{lane_id}-phoenix.jsonl"
        phoenix_row = _pull_phoenix_trace(
            trace_id=trace_id,
            out_jsonl=phoenix_jsonl,
            base_url=args.phoenix_base_url or None,
            timeout=min(30.0, args.timeout),
        )

        diagnostics_ok, diagnostics_body = _settings_source_test(
            base_url=args.base_url,
            timeout=min(30.0, args.timeout),
            source_id=str(spec["source_test_id"]),
        )
        _write_json(out_dir / f"{lane_id}-source-test.json", diagnostics_body)

        web_eval = evaluate_external_web_research_case(data) if lane_id == "external_web" and http_ok else {}
        tools_seen = tool_names_from_trace(
            data.get("tool_trace") if isinstance(data.get("tool_trace"), list) else []
        )
        issues = lane_issue_list(
            http_ok=http_ok,
            response_data=data if http_ok else {},
            expected_tools=expected_tools,
            phoenix_fetch_ok=bool(phoenix_row.get("fetch_ok")),
            diagnostics_ok=diagnostics_ok,
        )
        if lane_id == "external_web" and web_eval and not web_eval.get("ok"):
            issues.extend([f"web_evidence:{x}" for x in web_eval.get("issues") or []])

        lane_row = {
            "lane_id": lane_id,
            "gate_status": gate_status(issues),
            "issues": sorted(set(issues)),
            "expected_tools": list(expected_tools),
            "tools_seen": tools_seen,
            "phoenix_trace_id": trace_id,
            "phoenix": phoenix_row,
            "diagnostics_ok": diagnostics_ok,
            "web_eval": web_eval,
        }
        lane_rows.append(lane_row)
        _write_json(out_dir / f"{lane_id}-report.json", lane_row)
        _write_text(
            out_dir / f"{lane_id}-report.md",
            markdown_for_lane_report(
                lane_id=lane_id,
                expected_tools=expected_tools,
                tools_seen=tools_seen,
                phoenix_trace_id=trace_id,
                phoenix_fetch_ok=bool(phoenix_row.get("fetch_ok")),
                diagnostics_ok=diagnostics_ok,
                issues=lane_row["issues"],
            ),
        )

    # Direct API smokes for external providers / MCP.
    direct_smokes = {
        "openalex_api_smoke": [
            str(_REPO_ROOT / ".venv/bin/python"),
            str(_SCRIPT_DIR / "openalex_smoke.py"),
            "--query",
            "object detection",
            "--max-results",
            "1",
        ],
        "semantic_scholar_api_smoke": [
            str(_REPO_ROOT / ".venv/bin/python"),
            str(_SCRIPT_DIR / "semantic_scholar_smoke.py"),
            "--query",
            "attention is all you need",
        ],
        "mcp_adapter_smoke": [
            str(_REPO_ROOT / ".venv/bin/python"),
            str(_SCRIPT_DIR / "mcp_adapter_smoke.py"),
            "--server",
            "smoke",
        ],
    }
    direct_rows: dict[str, dict[str, Any]] = {}
    for key, command in direct_smokes.items():
        ok, output = _run_command(command)
        row = {"ok": ok, "command": command, "output_tail": "\n".join(output.splitlines()[-30:])}
        direct_rows[key] = row
        _write_json(out_dir / f"{key}.json", row)

    mcp_e2e_cmd = [
        str(_REPO_ROOT / ".venv/bin/python"),
        str(_SCRIPT_DIR / "mcp_agent_e2e_smoke.py"),
        "--skip-adapter-smoke",
    ]
    mcp_ok, mcp_output = _run_command(mcp_e2e_cmd)
    mcp_row = {
        "ok": mcp_ok,
        "command": mcp_e2e_cmd,
        "output_tail": "\n".join(mcp_output.splitlines()[-60:]),
    }
    _write_json(out_dir / "mcp_agent_e2e_smoke.json", mcp_row)

    root_report["lanes"] = {row["lane_id"]: row for row in lane_rows}
    root_report["direct_smokes"] = direct_rows
    root_report["mcp_agent_e2e"] = mcp_row
    root_report["closeout_gate_status"] = (
        "pass"
        if all(row["gate_status"] == "pass" for row in lane_rows)
        and all(row.get("ok") for row in direct_rows.values())
        and mcp_row["ok"]
        else "fail"
    )
    _write_json(out_dir / "index.json", root_report)

    lines = [
        "# External Research Closeout Index",
        "",
        f"- closeout_gate_status: `{root_report['closeout_gate_status']}`",
        f"- base_url: `{args.base_url.rstrip('/')}`",
        f"- workspace_id: `{args.workspace_id}`",
        "",
        "## Lanes",
    ]
    for row in lane_rows:
        lines.append(f"- `{row['lane_id']}`: `{row['gate_status']}` (`{', '.join(row['issues']) or 'none'}`)")
    lines.extend(["", "## Direct smokes"])
    for name, row in direct_rows.items():
        lines.append(f"- `{name}`: `{'pass' if row['ok'] else 'fail'}`")
    lines.append(f"- `mcp_agent_e2e_smoke`: `{'pass' if mcp_row['ok'] else 'fail'}`")
    lines.append("")
    _write_text(out_dir / "index.md", "\n".join(lines))

    print(str(out_dir))
    return 0 if root_report["closeout_gate_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
