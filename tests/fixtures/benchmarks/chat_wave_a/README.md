# Chat Wave A fixtures (starter)

Placeholder for future `chat_inventory_v1` / `chat_tool_selection_v1` harnesses.

**CI (Wave B):** `tests/eval/test_chat_wave_a_inventory.py` validates that gold files only reference tool names present in `TOOL_MANIFEST`.

- Intended shape: `question`, optional `workspace_id`, `expected_tool_sequence` or relaxed matchers.
- Wave A ships contract + tools + rule shortlist; a dedicated runner may land with CH9.

See [`docs/specs/agent-chat-v1.md`](../../../../docs/specs/agent-chat-v1.md).
