/**
 * Extract LLM token counts from agent `run_metadata` (sync with ChatMessageThread metadata dialog).
 *
 * @param {unknown} runMeta
 * @returns {{ totalTokens: number | null, promptTokens: number | null, completionTokens: number | null }}
 */
export function extractTokenCountsFromRunMetadata(runMeta) {
  const rm = runMeta && typeof runMeta === "object" ? runMeta : {};
  const usage = rm.usage && typeof rm.usage === "object" ? rm.usage : {};
  const pick = (...vals) => {
    for (const v of vals) {
      const n = Number(v);
      if (Number.isFinite(n) && n >= 0) return Math.round(n);
    }
    return null;
  };
  const promptTokens = pick(usage.prompt_tokens, usage.input_tokens, rm.prompt_tokens);
  const completionTokens = pick(usage.completion_tokens, usage.output_tokens, rm.completion_tokens);
  let totalTokens = pick(usage.total_tokens, rm.total_tokens, rm.token_count);
  if (totalTokens == null && promptTokens != null && completionTokens != null) {
    totalTokens = promptTokens + completionTokens;
  }
  return { totalTokens, promptTokens, completionTokens };
}
