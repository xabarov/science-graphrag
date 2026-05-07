"""Subagent completion envelope: XML + structured payload for transcript/SSE parity."""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Literal

from langchain_core.messages import HumanMessage

TaskStatus = Literal["completed", "failed", "cancelled", "timed_out"]


def new_task_id() -> str:
    return str(uuid.uuid4())


def _xml_escape(text: str) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@dataclass(frozen=True, slots=True)
class SubagentCarryBack:
    """Structured pull-back to parent (bounded; no full child transcript)."""

    summary: str
    result_excerpt: str | None = None
    key_sources: list[str] | None = None
    verdict: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary[:2000],
            "result_excerpt": (self.result_excerpt or "")[:8000] if self.result_excerpt else None,
            "key_sources": list(self.key_sources or [])[:64],
            "verdict": self.verdict,
        }


def build_carry_back_from_specialist_results(
    rows: list[dict[str, Any]] | None,
    *,
    max_chars: int = 4000,
) -> SubagentCarryBack:
    """Derive a bounded carry-back payload from specialist_results rows."""
    if not rows:
        return SubagentCarryBack(summary="No structured specialist payload recorded.")
    blob = rows[-1]
    if not isinstance(blob, dict):
        return SubagentCarryBack(summary="Specialist payload was non-dict; omitted details.")
    parts: list[str] = []
    bib = blob.get("bibliography")
    if isinstance(bib, dict):
        entries = bib.get("entries")
        if isinstance(entries, list) and entries:
            parts.append(f"bibliography_entries={len(entries)}")
        fw = bib.get("filtered_work_ids")
        if isinstance(fw, list) and fw:
            parts.append(f"filtered_work_ids={len(fw)}")
    summary = "; ".join(parts) if parts else "Specialist leg completed."
    raw = str(blob)[:max_chars]
    return SubagentCarryBack(summary=summary[:2000], result_excerpt=raw)


def build_task_notification_xml(
    *,
    task_id: str,
    subagent_id: str,
    parent_turn_id: str,
    status: TaskStatus,
    carry: SubagentCarryBack,
    usage: dict[str, Any] | None = None,
) -> str:
    """Build compaction-friendly task-notification XML (user-role transcript)."""
    u = usage or {}
    ti = _xml_escape(str(u.get("tokens_input") or ""))
    to_ = _xml_escape(str(u.get("tokens_output") or ""))
    dm = _xml_escape(str(u.get("duration_ms") or ""))
    summary = _xml_escape(carry.summary)
    excerpt = carry.result_excerpt or ""
    excerpt = excerpt[:12000].replace("]]>", "]] >")
    ks = carry.key_sources or []
    ks_xml = "".join(f"<source>{_xml_escape(str(s))}</source>" for s in ks[:32])
    verdict_xml = ""
    if carry.verdict:
        verdict_xml = f"<verdict>{_xml_escape(carry.verdict)}</verdict>"
    return (
        "<task-notification"
        f' task-id="{_xml_escape(task_id)}"'
        f' subagent="{_xml_escape(subagent_id)}"'
        f' parent-turn-id="{_xml_escape(parent_turn_id)}"'
        f' status="{status}">'
        f"<task-id>{_xml_escape(task_id)}</task-id>"
        f"<subagent>{_xml_escape(subagent_id)}</subagent>"
        f"<status>{status}</status>"
        "<usage>"
        f"<tokens-input>{ti}</tokens-input>"
        f"<tokens-output>{to_}</tokens-output>"
        f"<duration-ms>{dm}</duration-ms>"
        "</usage>"
        f"<summary>{summary}</summary>"
        f"<key-sources>{ks_xml}</key-sources>"
        f"{verdict_xml}"
        f"<result><![CDATA[{excerpt}]]></result>"
        "</task-notification>"
    )


def task_notification_human_message(
    *,
    task_id: str,
    subagent_id: str,
    parent_turn_id: str,
    status: TaskStatus,
    carry: SubagentCarryBack,
    usage: dict[str, Any] | None = None,
) -> HumanMessage:
    """LangGraph HumanMessage carrying XML + mirrored structured kwargs."""
    xml = build_task_notification_xml(
        task_id=task_id,
        subagent_id=subagent_id,
        parent_turn_id=parent_turn_id,
        status=status,
        carry=carry,
        usage=usage,
    )
    payload = {
        "schema_version": 1,
        "task_id": task_id,
        "subagent_id": subagent_id,
        "parent_turn_id": parent_turn_id,
        "status": status,
        "carry_back": carry.to_dict(),
        "usage": usage or {},
    }
    return HumanMessage(
        content=xml,
        additional_kwargs={
            "kind": "task_notification",
            "task_notification": payload,
        },
    )


def sse_payload_claim_verification_from_human_message(msg: HumanMessage) -> dict[str, Any] | None:
    """SSE ``claim_verification_result`` dict from a HumanMessage (mirrors task_notification pattern)."""
    if not isinstance(msg, HumanMessage):
        return None
    ak = getattr(msg, "additional_kwargs", None) or {}
    if not isinstance(ak, dict):
        return None
    if str(ak.get("kind") or "") != "claim_verification_result":
        return None
    inner = ak.get("claim_verification_result")
    if not isinstance(inner, dict):
        return None
    merged = {k: v for k, v in inner.items() if k != "type"}
    return {**merged, "type": "claim_verification_result"}


def sse_payload_from_human_message(msg: HumanMessage) -> dict[str, Any] | None:
    """Extract SSE ``subagent_task_notification`` dict from a HumanMessage."""
    if not isinstance(msg, HumanMessage):
        return None
    ak = getattr(msg, "additional_kwargs", None) or {}
    if not isinstance(ak, dict):
        return None
    if str(ak.get("kind") or "") != "task_notification":
        return None
    inner = ak.get("task_notification")
    if not isinstance(inner, dict):
        return None
    merged = {k: v for k, v in inner.items() if k != "type"}
    return {
        **merged,
        "type": "subagent_task_notification",
        "xml_excerpt": str(msg.content or "")[:2000],
    }


def parse_task_notification_xml(xml: str) -> dict[str, Any] | None:
    """Best-effort parse for tests / trace-review (prefer structured kwargs when present)."""
    if not xml or "<task-notification" not in xml:
        return None
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return None
    if root.tag != "task-notification":
        return None
    task_id = root.attrib.get("task-id") or ""
    subagent = root.attrib.get("subagent") or ""
    parent_turn = root.attrib.get("parent-turn-id") or ""
    status = root.attrib.get("status") or ""
    summary_el = root.find("summary")
    summary = str(summary_el.text or "").strip() if summary_el is not None else ""
    return {
        "task_id": task_id,
        "subagent_id": subagent,
        "parent_turn_id": parent_turn,
        "status": status,
        "summary": summary,
    }


__all__ = [
    "SubagentCarryBack",
    "build_carry_back_from_specialist_results",
    "build_task_notification_xml",
    "new_task_id",
    "parse_task_notification_xml",
    "sse_payload_claim_verification_from_human_message",
    "sse_payload_from_human_message",
    "task_notification_human_message",
]
