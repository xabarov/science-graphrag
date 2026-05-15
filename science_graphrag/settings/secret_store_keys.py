"""Canonical persisted secret store key names (runtime settings UI)."""

# Managed OpenAI-compatible API key for extraction / chat (see SettingsService).
LLM_API_KEY = "llm.api_key"
# Optional separate key for VL PDF→Markdown when operators need a different provider key.
LLM_VISION_API_KEY = "llm.vision_api_key"

__all__ = ["LLM_API_KEY", "LLM_VISION_API_KEY"]
