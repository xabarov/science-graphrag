"""Static settings UI section catalog for ``SettingsService.get_snapshot``."""

from __future__ import annotations

from typing import Any


def build_settings_sections_catalog() -> list[dict[str, Any]]:
    """Return the ordered list of settings SPA sections (ids, labels, descriptions)."""
    return [
        {
            "id": "general",
            "label": "General",
            "status": "ready",
            "description": (
                "Interface language, appearance, and server-managed OpenAlex contact email."
            ),
        },
        {
            "id": "llm",
            "label": "LLM",
            "status": "ready",
            "description": "Provider endpoint, model defaults, credentials, and test tools.",
        },
        {
            "id": "ingestion",
            "label": "Ingestion",
            "status": "ready",
            "description": "Workspace file uploads and related limits.",
        },
        {
            "id": "storage",
            "label": "Storage & Integrations",
            "status": "ready",
            "description": ("Neo4j, Qdrant, Postgres, Redis, object storage, and local paths."),
        },
        {
            "id": "benchmark",
            "label": "Benchmark",
            "status": "ready",
            "description": ("Teacher/student defaults and benchmark-specific execution knobs."),
        },
        {
            "id": "security",
            "label": "Security & Access",
            "status": "ready",
            "description": "Read-only flags for admin and settings API protection.",
        },
        {
            "id": "diagnostics",
            "label": "Diagnostics",
            "status": "ready",
            "description": "Runtime build identity (read-only).",
        },
        {
            "id": "agent_tools",
            "label": "Agent tools",
            "status": "ready",
            "description": (
                "External scholarly research defaults, PDF policy, MCP integration flags, "
                "supervisor limits, and diagnostics (separate from LLM provider settings)."
            ),
        },
    ]
