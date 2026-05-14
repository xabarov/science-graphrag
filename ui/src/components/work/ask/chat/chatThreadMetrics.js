import { extractTokenCountsFromRunMetadata } from "../answer/runMetadataUsage.js";

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

function pickOpenrouterRefPricing(runMeta) {
  const block = runMeta.openrouter_reference_pricing_usd_per_1m;
  if (!block || typeof block !== "object") {
    return { openrouterChatRefPricing: null, openrouterExtractionRefPricing: null };
  }

  const fmt = (row) => {
    if (!row || typeof row !== "object") return null;
    const model = typeof row.model_id === "string" ? row.model_id : "";
    const p = toFiniteNumber(row.prompt_usd_per_1m);
    const c = toFiniteNumber(row.completion_usd_per_1m);
    if (!model || p == null || c == null) return null;
    return {
      model,
      prompt: p.toLocaleString(undefined, { maximumFractionDigits: 4 }),
      completion: c.toLocaleString(undefined, { maximumFractionDigits: 4 }),
    };
  };

  return {
    openrouterChatRefPricing: fmt(block.chat),
    openrouterExtractionRefPricing: fmt(block.extraction),
  };
}

/**
 * When the API does not return usage.cost_usd, approximate USD cost from aggregate prompt/completion
 * tokens and OpenRouter list $/1M from run_metadata. Chat + extraction share one merged usage blob,
 * so when both models are listed we blend their list rates (midpoint) — a deliberate underestimate
 * for some splits and overestimate for others, but stable for UI totals.
 *
 * @param {Record<string, unknown>} runMeta
 * @param {number | null} promptTokens
 * @param {number | null} completionTokens
 * @returns {number | null}
 */
export function estimateCostUsdFromOpenrouterReference(runMeta, promptTokens, completionTokens) {
  const block = runMeta?.openrouter_reference_pricing_usd_per_1m;
  if (!block || typeof block !== "object") return null;
  if (promptTokens == null || completionTokens == null) return null;
  if (promptTokens < 0 || completionTokens < 0) return null;

  const pRate = (row) => {
    if (!row || typeof row !== "object") return null;
    const pp = toFiniteNumber(row.prompt_usd_per_1m);
    const cc = toFiniteNumber(row.completion_usd_per_1m);
    if (pp == null || cc == null) return null;
    return { pp, cc };
  };

  const chat = pRate(block.chat);
  const extraction = pRate(block.extraction);
  const pm = promptTokens / 1e6;
  const cm = completionTokens / 1e6;

  if (chat && extraction) {
    const avgPrompt = (chat.pp + extraction.pp) / 2;
    const avgComp = (chat.cc + extraction.cc) / 2;
    return pm * avgPrompt + cm * avgComp;
  }
  const one = chat || extraction;
  if (!one) return null;
  return pm * one.pp + cm * one.cc;
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
  const reportedCostUsd = pickNumber(usage.cost_usd, usage.usd_cost, runMeta.cost_usd, runMeta.usd_cost);
  const estimatedCostUsd = estimateCostUsdFromOpenrouterReference(runMeta, promptTokens, completionTokens);
  const costUsd = reportedCostUsd ?? estimatedCostUsd ?? null;
  const costUsdIsEstimated = reportedCostUsd == null && estimatedCostUsd != null;
  const { openrouterChatRefPricing, openrouterExtractionRefPricing } = pickOpenrouterRefPricing(runMeta);
  return {
    durationMs,
    totalTokens,
    promptTokens,
    completionTokens,
    tokensPerSecond,
    costUsd,
    costUsdIsEstimated,
    openrouterChatRefPricing,
    openrouterExtractionRefPricing,
  };
}
