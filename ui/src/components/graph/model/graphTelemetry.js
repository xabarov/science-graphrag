/**
 * Opt-in graph diagnostics: set localStorage `science-graphrag:graphTelemetry=1`
 * or run a dev build (import.meta.env.DEV) to log classification events for
 * fetch vs topology vs layout / React Flow.
 */

const LS_GRAPH_TELEMETRY = "science-graphrag:graphTelemetry";

/**
 * @returns {boolean}
 */
export function isGraphTelemetryEnabled() {
  if (typeof window === "undefined") return false;
  try {
    if (window.localStorage?.getItem(LS_GRAPH_TELEMETRY) === "1") return true;
  } catch {
    /* ignore */
  }
  try {
    return Boolean(import.meta.env?.DEV);
  } catch {
    return false;
  }
}

/**
 * @param {string} kind
 * @param {Record<string, unknown>} [detail]
 */
export function graphTelemetryEmit(kind, detail = {}) {
  if (!isGraphTelemetryEnabled()) return;
  // eslint-disable-next-line no-console -- dev-only diagnostics
  console.debug(`[graphTelemetry] ${kind}`, detail);
}
