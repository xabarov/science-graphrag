"""Static settings UI section catalog for ``SettingsService.get_snapshot``."""

from __future__ import annotations

from typing import Any


def build_settings_sections_catalog() -> list[dict[str, Any]]:
    """Return the ordered list of settings SPA sections (ids, labels, descriptions)."""
    return [
        {
            "id": "general",
            "label": "General",
            "description": (
                "Interface language, appearance, and server-managed OpenAlex contact email."
            ),
        },
        {
            "id": "llm",
            "label": "LLM",
            "description": "Provider endpoint, model defaults, credentials, and test tools.",
        },
        {
            "id": "ingestion",
            "label": "Ingestion",
            "description": "Workspace file uploads and related limits.",
        },
        {
            "id": "storage",
            "label": "Storage & Integrations",
            "description": ("Neo4j, Qdrant, Postgres, Redis, object storage, and local paths."),
        },
        {
            "id": "benchmark",
            "label": "Benchmark",
            "description": ("Teacher/student defaults and benchmark-specific execution knobs."),
        },
        {
            "id": "security",
            "label": "Security & Access",
            "description": "Read-only flags for admin and settings API protection.",
        },
        {
            "id": "diagnostics",
            "label": "Diagnostics",
            "description": "Runtime build identity (read-only).",
        },
        {
            "id": "agent_tools",
            "label": "Agent tools",
            "description": (
                "External scholarly research defaults, PDF policy, MCP integration flags, "
                "supervisor limits, and diagnostics (separate from LLM provider settings)."
            ),
        },
    ]
