"""Canonical persisted secret store key names (runtime settings UI)."""

# Managed OpenAI-compatible API key for extraction / chat (see SettingsService).
LLM_API_KEY = "llm.api_key"
# Optional dedicated key for research chat task.
LLM_CHAT_API_KEY = "llm.chat_api_key"
# Optional separate key for VL PDF→Markdown when operators need a different provider key.
LLM_VISION_API_KEY = "llm.vision_api_key"
# Optional dedicated key for OpenRouter embeddings task.
LLM_EMBEDDINGS_API_KEY = "llm.embeddings_api_key"
# Optional Semantic Scholar API key (higher rate limits for native S2 tools).
SEMANTIC_SCHOLAR_API_KEY = "agent_tools.semantic_scholar_api_key"

__all__ = [
    "LLM_API_KEY",
    "LLM_CHAT_API_KEY",
    "LLM_VISION_API_KEY",
    "LLM_EMBEDDINGS_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
]
