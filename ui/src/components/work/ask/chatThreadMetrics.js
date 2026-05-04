import { extractTokenCountsFromRunMetadata } from "./runMetadataUsage.js";

export const SCROLL_BOTTOM_THRESHOLD_PX = 80;

export function toFiniteNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

export function pickNumber(...vals) {
  for (const v of vals) {
    const n = toFiniteNumber(v);
    if (n != null) return n;
  }
  return null;
}

export function formatMetricValue(value, { unit = "", digits = 0 } = {}) {
  const n = toFiniteNumber(value);
  if (n == null) return "—";
  return `${n.toLocaleString(undefined, { maximumFractionDigits: digits })}${unit}`;
}

export function extractTurnMetadata(entry) {
  const details = entry?.details && typeof entry.details === "object" ? entry.details : {};
  const runMeta = details.run_metadata && typeof details.run_metadata === "object" ? details.run_metadata : {};
  const usage = runMeta.usage && typeof runMeta.usage === "object" ? runMeta.usage : {};
  const { totalTokens: ttFromRm, promptTokens: ptFromRm, completionTokens: ctFromRm } =
    extractTokenCountsFromRunMetadata(runMeta);
  const promptTokens = pickNumber(ptFromRm, usage.prompt_tokens, usage.input_tokens, runMeta.prompt_tokens);
  const completionTokens = pickNumber(ctFromRm, usage.completion_tokens, usage.output_tokens, runMeta.completion_tokens);
  const totalTokens = pickNumber(
    ttFromRm,
    usage.total_tokens,
    runMeta.total_tokens,
    runMeta.token_count,
    promptTokens != null && completionTokens != null ? promptTokens + completionTokens : null,
  );
  const durationMs = pickNumber(details.duration_ms, runMeta.duration_ms);
  let tokensPerSecond = pickNumber(usage.tokens_per_second, usage.tps, runMeta.tokens_per_second, runMeta.tps);
  if (
    tokensPerSecond == null &&
    durationMs != null &&
    durationMs > 0 &&
    totalTokens != null &&
    totalTokens > 0
  ) {
    tokensPerSecond = (totalTokens * 1000) / durationMs;
  }
  const costUsd = pickNumber(usage.cost_usd, usage.usd_cost, runMeta.cost_usd, runMeta.usd_cost);
  const eventsCount = Array.isArray(details.stream_events) ? details.stream_events.length : 0;
  const citationCount = Array.isArray(details.citations) ? details.citations.length : pickNumber(entry?.citationCount) || 0;
  const answerClass = String(details.answer_class || "").trim();
  return {
    durationMs,
    totalTokens,
    promptTokens,
    completionTokens,
    tokensPerSecond,
    costUsd,
    eventsCount,
    citationCount,
    answerClass,
  };
}
