/** Order matches backend ``LLM_ADVANCED_RUNTIME_KEYS`` (Phase 3). */
export const LLM_RUNTIME_OVERRIDE_KEYS = [
  "llm_concurrency_default",
  "llm_concurrency_translation",
  "llm_concurrency_extraction_references",
  "llm_concurrency_claims",
  "llm_concurrency_summary",
  "llm_concurrency_semantic",
  "llm_concurrency_dedup",
  "llm_concurrency_agent_chat",
  "llm_concurrency_agent_classifier",
  "llm_concurrency_query_answer",
  "extraction_llm_references_max_concurrency",
  "agent_step_timeout_seconds",
  "agent_turn_policy_classifier_timeout_seconds",
  "work_dedup_llm_timeout_s",
  "author_dedup_llm_timeout_s",
  "agent_chat_max_retries",
  "agent_classifier_max_retries",
  "agent_graph_invoke_max_workers",
  "agent_min_llm_hop_reserve_seconds",
  "llm_distributed_quota_enabled",
  "llm_distributed_quota_key_prefix",
  "llm_distributed_quota_acquire_timeout_seconds",
  "llm_distributed_quota_lease_seconds",
  "agent_runtime",
  "agent_max_tool_calls",
  "agent_turn_policy_llm_enabled",
];

export const LLM_ADVANCED_GROUPS = {
  llm_concurrency: "llm.advanced.group.concurrency",
  llm_distributed_quota: "llm.advanced.group.distributedQuota",
  llm_deadlines: "llm.advanced.group.deadlines",
  llm_agent_runtime: "llm.advanced.group.agentRuntime",
};

/** @param {string} key */
export function schemaGroupForKey(key, schemaFields) {
  const row = (schemaFields || []).find((f) => f.id === key);
  return row?.group || "llm_advanced";
}
