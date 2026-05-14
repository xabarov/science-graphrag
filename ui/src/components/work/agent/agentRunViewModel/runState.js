function normalizedHasDegraded(normalized) {
  if (!normalized || typeof normalized !== "object") return false;
  const rt = normalized.retrieval_trace;
  const gc = normalized.graph_context;
  const rtDeg = rt && typeof rt === "object" && Array.isArray(rt.degraded) && rt.degraded.length > 0;
  const gcDeg = gc && typeof gc === "object" && Array.isArray(gc.degraded) && gc.degraded.length > 0;
  return Boolean(rtDeg || gcDeg);
}

function streamHasErrorEvent(streamEvents) {
  if (!Array.isArray(streamEvents)) return false;
  return streamEvents.some((e) => e && typeof e === "object" && String(e.type || "") === "error");
}

/**
 * @param {{
 *   normalized: Record<string, unknown> | null | undefined,
 *   isRunActive: boolean,
 *   streamEvents?: unknown[],
 * }} input
 * @returns {{
 *   runState: 'running' | 'done' | 'warning' | 'degraded' | 'failed',
 *   streamWarningCount: number,
 * }}
 */
export function deriveRunState({ normalized, isRunActive, streamEvents = [] }) {
  const warnings = normalized && Array.isArray(normalized.warnings) ? normalized.warnings : [];
  const streamWarnings = Array.isArray(streamEvents)
    ? streamEvents.filter((e) => e && typeof e === "object" && e.type === "warning").length
    : 0;
  if (isRunActive) return { runState: "running", streamWarningCount: streamWarnings };
  if (streamHasErrorEvent(streamEvents)) return { runState: "failed", streamWarningCount: streamWarnings };
  if (warnings.length > 0 || streamWarnings > 0) return { runState: "warning", streamWarningCount: streamWarnings };
  if (normalizedHasDegraded(normalized)) return { runState: "degraded", streamWarningCount: streamWarnings };
  return { runState: "done", streamWarningCount: streamWarnings };
}

/**
 * @param {{
 *   normalized: Record<string, unknown>,
 *   streamEvents?: unknown[],
 *   agentToolTrace?: unknown[],
 *   retrievalMode?: string,
 * }} input
 * @returns {boolean}
 */
export function shouldOfferRunInspector({ normalized, streamEvents = [], agentToolTrace = [], retrievalMode }) {
  if (retrievalMode !== "agent") return false;
  if (!normalized || typeof normalized !== "object") return false;
  const hasTrace = Array.isArray(agentToolTrace) && agentToolTrace.length > 0;
  const hasEvents = Array.isArray(streamEvents) && streamEvents.length > 0;
  const gc = normalized.graph_context;
  const rt = normalized.retrieval_trace;
  const graphRich = Boolean(
    gc &&
      typeof gc === "object" &&
      ((Array.isArray(gc.methods) && gc.methods.length > 0) ||
        (Array.isArray(gc.datasets) && gc.datasets.length > 0) ||
        (Array.isArray(gc.degraded) && gc.degraded.length > 0) ||
        Boolean(gc.error)),
  );
  const rtRich = Boolean(
    rt &&
      typeof rt === "object" &&
      (Number(rt.hit_count) > 0 ||
        Number(rt.citations_returned) > 0 ||
        (Array.isArray(rt.degraded) && rt.degraded.length > 0) ||
        Boolean(rt.retrieval_policy)),
  );
  return Boolean(hasTrace || hasEvents || graphRich || rtRich);
}
