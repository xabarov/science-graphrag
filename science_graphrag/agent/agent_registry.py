"""Disk-loaded SciGraph agent definitions (Train T3 §10.7).

Loads ``~/.scigraph/agents/*.md`` and optional workspace paths
``<dir>/.scigraph/agents/*.md``. Later sources override earlier by ``name``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from science_graphrag.agent.can_use_tool_contract import CanUseTool
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name

PermissionMode = Literal["read_only", "default", "full"]


@dataclass(frozen=True, slots=True)
class DiskAgentDefinition:
    """Parsed agent markdown + frontmatter."""

    name: str
    source_path: str
    model: str | None = None
    tools: tuple[str, ...] = field(default_factory=tuple)
    disallowed_tools: tuple[str, ...] = field(default_factory=tuple)
    permission_mode: PermissionMode = "default"
    when_to_use: str = ""
    color: str | None = None
    isolation: str | None = None
    background: bool = False
    system_prompt_body: str = ""


def _default_user_agents_dir() -> Path:
    return Path.home() / ".scigraph" / "agents"


def _parse_frontmatter_md(raw: str) -> tuple[dict[str, Any], str]:
    text = raw.lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    fm_raw, body = m.group(1), m.group(2)
    try:
        data = yaml.safe_load(fm_raw) or {}
    except yaml.YAMLError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    return data, body


def _coerce_str_list(val: Any) -> tuple[str, ...]:
    if val is None:
        return ()
    if isinstance(val, str):
        s = normalize_tool_call_name(val)
        return (s,) if s else ()
    if isinstance(val, list):
        out: list[str] = []
        seen: set[str] = set()
        for x in val:
            s = normalize_tool_call_name(str(x))
            if s and s not in seen:
                out.append(s)
                seen.add(s)
        return tuple(out)
    return ()


def _coerce_permission_mode(val: Any) -> PermissionMode:
    s = str(val or "").strip().lower()
    if s in ("read_only", "readonly", "read-only"):
        return "read_only"
    if s in ("full", "all"):
        return "full"
    return "default"


def parse_disk_agent_file(path: Path) -> DiskAgentDefinition:
    """Parse a single ``*.md`` agent definition."""
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"agent file is not valid utf-8: {path}") from exc
    fm, body = _parse_frontmatter_md(raw)
    name = str(fm.get("name") or path.stem).strip()
    if not name:
        name = path.stem
    return DiskAgentDefinition(
        name=name,
        source_path=str(path.resolve()),
        model=str(fm["model"]).strip() if fm.get("model") is not None else None,
        tools=_coerce_str_list(fm.get("tools")),
        disallowed_tools=_coerce_str_list(fm.get("disallowedTools") or fm.get("disallowed_tools")),
        permission_mode=_coerce_permission_mode(
            fm.get("permissionMode") or fm.get("permission_mode")
        ),
        when_to_use=str(fm.get("whenToUse") or fm.get("when_to_use") or "").strip(),
        color=str(fm["color"]).strip() if fm.get("color") is not None else None,
        isolation=str(fm["isolation"]).strip() if fm.get("isolation") is not None else None,
        background=bool(fm.get("background")),
        system_prompt_body=body.strip(),
    )


def load_disk_agent_definitions(
    *,
    workspace_agent_roots: tuple[Path, ...] | None = None,
    extra_user_dirs: tuple[Path, ...] | None = None,
) -> dict[str, DiskAgentDefinition]:
    """Load and merge definitions (workspace roots override user defaults)."""
    merged: dict[str, DiskAgentDefinition] = {}
    dirs: list[Path] = []
    if extra_user_dirs:
        dirs.extend(Path(p).expanduser() for p in extra_user_dirs)
    else:
        dirs.append(_default_user_agents_dir())
    for root in dirs:
        if root.is_dir():
            for p in sorted(root.glob("*.md")):
                if p.is_file():
                    try:
                        dfn = parse_disk_agent_file(p)
                        merged[dfn.name] = dfn
                    except (OSError, ValueError, TypeError, yaml.YAMLError):
                        continue
    for ws in workspace_agent_roots or ():
        agents_dir = (Path(ws).expanduser() / ".scigraph" / "agents").resolve()
        if not agents_dir.is_dir():
            continue
        for p in sorted(agents_dir.glob("*.md")):
            if p.is_file():
                try:
                    dfn = parse_disk_agent_file(p)
                    merged[dfn.name] = dfn
                except (OSError, ValueError, TypeError, yaml.YAMLError):
                    continue
    return merged


def build_system_prompt_for_disk_agent(defn: DiskAgentDefinition) -> str:
    """Compose system prompt from definition (body + compact metadata block)."""
    meta_lines = [
        f"You are the SciGraph disk-defined agent `{defn.name}`.",
        f"permission_mode={defn.permission_mode}",
    ]
    if defn.tools:
        meta_lines.append("allowed_catalog_tools: " + ", ".join(defn.tools))
    if defn.disallowed_tools:
        meta_lines.append("disallowed_catalog_tools: " + ", ".join(defn.disallowed_tools))
    if defn.when_to_use:
        meta_lines.append("when_to_use: " + defn.when_to_use[:500])
    block = "\n".join(meta_lines)
    body = (defn.system_prompt_body or "").strip()
    if body:
        return block + "\n\n" + body
    return block


def disk_agent_definition_to_can_use_tool(defn: DiskAgentDefinition) -> CanUseTool:
    """Map frontmatter lists to per-call deny reasons (on top of matrix / bound surface)."""

    denied = {normalize_tool_call_name(x) for x in defn.disallowed_tools if str(x).strip()}
    allowed = {normalize_tool_call_name(x) for x in defn.tools if str(x).strip()}

    def _can_use_tool(_state: Any, tool_name: str, _tool_call: dict[str, Any]) -> str | None:
        n = normalize_tool_call_name(tool_name)
        if n in denied:
            return f"tool_denied_by_registry:disallowed:{n}"
        if allowed and n not in allowed:
            return f"tool_denied_by_registry:not_whitelisted:{n}"
        return None

    return _can_use_tool


__all__ = [
    "DiskAgentDefinition",
    "PermissionMode",
    "build_system_prompt_for_disk_agent",
    "disk_agent_definition_to_can_use_tool",
    "load_disk_agent_definitions",
    "parse_disk_agent_file",
]
