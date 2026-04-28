#!/usr/bin/env python3
"""Assemble research-chat system prompt + LangChain tool descriptions/schemas; print metrics.

Run from repository root (examples):

    .venv/bin/python scripts/prompt_audit/build_research_chat_prompt_bundle.py
    .venv/bin/python scripts/prompt_audit/build_research_chat_prompt_bundle.py \\
        --output /tmp/bundle.md
    .venv/bin/python scripts/prompt_audit/build_research_chat_prompt_bundle.py --json
    .venv/bin/python scripts/prompt_audit/build_research_chat_prompt_bundle.py --evaluate

Uses mocked stores (no Neo4j/Qdrant). Output approximates what providers see alongside
``bind_tools`` (names, descriptions, JSON Schema for arguments).

``--evaluate`` checks tool set, non-empty descriptions, and coarse size gates (exit 1 on failure).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Repo root on sys.path when run as file
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from unittest.mock import MagicMock

from science_graphrag.agent.prompts.research_chat_system import RESEARCH_CHAT_SYSTEM_PROMPT
from science_graphrag.agent.tools import build_tool_registry

EXPECTED_TOOL_NAMES = frozenset(
    {
        "cypher_query",
        "edge_search",
        "final_answer",
        "find_works",
        "format_bibliography_gost",
        "idea_search",
        "paper_profile",
        "paper_quote_search",
        "workspace_graph_reltypes",
        "workspace_inspect",
    }
)


def _fake_stores() -> MagicMock:
    stores = MagicMock()
    stores.neo4j = MagicMock()
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()
    return stores


def _token_words(text: str, min_len: int = 5) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_\-]+", text) if len(w) >= min_len}


def _approx_tokens(chars: int) -> int:
    # Rough heuristic (~4 chars per token for English-ish text + JSON)
    return max(1, chars // 4)


def _tool_bundle(tools: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in tools:
        name = getattr(t, "name", "") or ""
        desc = (getattr(t, "description", None) or "").strip()
        schema: dict[str, Any] | None = None
        args_schema = getattr(t, "args_schema", None)
        if args_schema is not None and hasattr(args_schema, "model_json_schema"):
            schema = args_schema.model_json_schema()
        out.append({"name": name, "description": desc, "args_schema": schema})
    return out


def _full_audit_report_markdown(
    system: str, bundle: list[dict[str, Any]], metrics: dict[str, Any]
) -> str:
    """Markdown bundle plus metrics appendix (same shape for file output and stdout)."""
    md = _render_markdown(system, bundle)
    report = [
        md,
        "---",
        "## Metrics (heuristic)",
        "",
        "```json",
        json.dumps(metrics, indent=2, ensure_ascii=False),
        "```",
        "",
        "### Interpretation",
        "",
        "- **overlap_ratio**: share of tool-description tokens (length≥5) that also appear in the",
        "  system prompt. High overlap is normal for repeated words (`workspace`, `work_id`).",
        "- **approx_input_tokens_***: crude `chars//4` — compare runs, not billing.",
        "- **tools_missing_description**: should be empty; LangChain uses description in JSON.",
        "",
    ]
    return "\n".join(report)


def _render_markdown(system: str, bundle: list[dict[str, Any]]) -> str:
    lines: list[str] = [
        "# Research chat agent — prompt bundle (audit)",
        "",
        "## System prompt",
        "",
        "```text",
        system.rstrip(),
        "```",
        "",
        "## Tools (bind_tools surface)",
        "",
    ]
    for item in bundle:
        lines.append(f"### `{item['name']}`")
        lines.append("")
        lines.append("**Description (docstring → provider)**")
        lines.append("")
        lines.append("```text")
        lines.append((item["description"] or "(empty)").strip())
        lines.append("```")
        lines.append("")
        if item.get("args_schema"):
            lines.append("**Args JSON Schema**")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(item["args_schema"], indent=2, ensure_ascii=False))
            lines.append("```")
        lines.append("")
    return "\n".join(lines)


def _metrics(system: str, bundle: list[dict[str, Any]]) -> dict[str, Any]:
    sys_words = _token_words(system)
    schema_chars = 0
    for x in bundle:
        sch = x.get("args_schema")
        if sch:
            schema_chars += len(json.dumps(sch, ensure_ascii=False))
    desc_chars = sum(len(x["description"] or "") for x in bundle)
    missing_desc = [x["name"] for x in bundle if not (x.get("description") or "").strip()]

    overlaps: list[dict[str, Any]] = []
    for x in bundle:
        desc = x.get("description") or ""
        dw = _token_words(desc)
        if not dw:
            overlaps.append({"tool": x["name"], "overlap_ratio": None, "shared_with_system": []})
            continue
        shared = sorted(dw & sys_words)
        overlaps.append(
            {
                "tool": x["name"],
                "overlap_ratio": round(len(shared) / len(dw), 3),
                "shared_with_system": shared[:24],
            }
        )

    total_chars = len(system) + desc_chars + schema_chars
    return {
        "system_prompt_chars": len(system),
        "tool_descriptions_total_chars": desc_chars,
        "tool_schemas_json_chars": schema_chars,
        "bundle_total_chars": total_chars,
        "approx_input_tokens_system_only": _approx_tokens(len(system)),
        "approx_input_tokens_tools_surface": _approx_tokens(desc_chars + schema_chars),
        "approx_input_tokens_bundle_total": _approx_tokens(total_chars),
        "tool_count": len(bundle),
        "tools_missing_description": missing_desc,
        "description_vs_system_word_overlap": overlaps,
    }


def evaluate_research_chat_bundle(
    metrics: dict[str, Any], bundle: list[dict[str, Any]]
) -> tuple[bool, list[str]]:
    """Return (all_checks_passed, human messages). Soft warnings do not fail."""
    msgs: list[str] = []
    hard_fail = False
    names = {x["name"] for x in bundle}
    if names != EXPECTED_TOOL_NAMES:
        hard_fail = True
        diff = sorted(names.symmetric_difference(EXPECTED_TOOL_NAMES))
        msgs.append(f"FAIL: tool name set mismatch: {diff}")
    if metrics.get("tools_missing_description"):
        hard_fail = True
        msgs.append(f"FAIL: tools missing description: {metrics['tools_missing_description']}")
    approx = int(metrics.get("approx_input_tokens_bundle_total") or 0)
    if approx > 14_000:
        hard_fail = True
        msgs.append(f"FAIL: bundle too large (approx_tokens={approx} > 14000)")
    elif approx > 10_000:
        msgs.append(f"WARN: large bundle (approx_tokens={approx} > 10000)")

    high_overlap = [
        x["tool"]
        for x in metrics.get("description_vs_system_word_overlap") or []
        if isinstance(x.get("overlap_ratio"), float) and x["overlap_ratio"] >= 0.95
    ]
    if high_overlap:
        msgs.append(
            "WARN: very high description/system token overlap for: "
            + ", ".join(high_overlap)
            + " (consider shortening tool docstrings)"
        )

    if not hard_fail:
        msgs.insert(0, "PASS: research chat prompt bundle checks OK.")
    return not hard_fail, msgs


def main() -> int:
    """CLI: print markdown bundle, JSON metrics, or run ``--evaluate`` gates."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Write markdown bundle to this path (UTF-8).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print only JSON metrics to stdout (no markdown).",
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Run size/tool-set gates; print PASS/WARN/FAIL lines; exit 1 on failure.",
    )
    args = parser.parse_args()

    tools = build_tool_registry(_fake_stores())
    bundle = _tool_bundle(tools)
    metrics = _metrics(RESEARCH_CHAT_SYSTEM_PROMPT, bundle)

    if args.evaluate:
        ok, lines = evaluate_research_chat_bundle(metrics, bundle)
        for line in lines:
            print(line, file=sys.stderr)
        if args.output:
            full = _full_audit_report_markdown(RESEARCH_CHAT_SYSTEM_PROMPT, bundle, metrics)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(full, encoding="utf-8")
            print(f"Wrote {args.output}", file=sys.stderr)
        if args.json:
            out = dict(metrics)
            out["evaluate_ok"] = ok
            out["evaluate_messages"] = lines
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(metrics, indent=2, ensure_ascii=False), file=sys.stderr)
        return 0 if ok else 1

    if args.json:
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
        return 0

    full = _full_audit_report_markdown(RESEARCH_CHAT_SYSTEM_PROMPT, bundle, metrics)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(full, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    print(full)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
