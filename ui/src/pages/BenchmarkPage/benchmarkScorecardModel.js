/**
 * Client-side normalization for future API `scorecards` / `primary_metrics` payloads (scorecard contract).
 * When the backend only returns a flat metrics object, callers still get stable buckets.
 *
 * @param {Record<string, unknown> | null | undefined} payload
 * @returns {{
 *   primary: Record<string, unknown>,
 *   secondary: Record<string, unknown>,
 *   diagnostic: Record<string, unknown>,
 *   definitions: Record<string, unknown> | null,
 *   scorecards: unknown,
 *   raw: Record<string, unknown> | null,
 * }}
 */
export function normalizeBenchmarkMetricsPayload(payload) {
  if (!payload || typeof payload !== "object") {
    return {
      primary: {},
      secondary: {},
      diagnostic: {},
      definitions: null,
      scorecards: null,
      raw: payload ?? null,
    };
  }
  const pm = payload.primary_metrics ?? payload.primaryMetrics;
  const secondaryObj =
    (payload.secondary_metrics && typeof payload.secondary_metrics === "object" && !Array.isArray(payload.secondary_metrics)
      ? payload.secondary_metrics
      : null) ||
    (payload.secondaryMetrics && typeof payload.secondaryMetrics === "object" && !Array.isArray(payload.secondaryMetrics)
      ? payload.secondaryMetrics
      : null) ||
    null;
  const diagnosticObj =
    (payload.diagnostic_metrics && typeof payload.diagnostic_metrics === "object" && !Array.isArray(payload.diagnostic_metrics)
      ? payload.diagnostic_metrics
      : null) ||
    (payload.diagnosticMetrics && typeof payload.diagnosticMetrics === "object" && !Array.isArray(payload.diagnosticMetrics)
      ? payload.diagnosticMetrics
      : null) ||
    null;
  const definitionsObj =
    (payload.metric_definitions &&
      typeof payload.metric_definitions === "object" &&
      !Array.isArray(payload.metric_definitions) &&
      payload.metric_definitions) ||
    (payload.metricDefinitions &&
      typeof payload.metricDefinitions === "object" &&
      !Array.isArray(payload.metricDefinitions) &&
      payload.metricDefinitions) ||
    null;

  if (pm && typeof pm === "object") {
    return {
      primary: pm,
      secondary: secondaryObj || {},
      diagnostic: diagnosticObj || {},
      definitions: definitionsObj,
      scorecards: payload.scorecards ?? null,
      raw: payload,
    };
  }
  if (
    (secondaryObj && Object.keys(secondaryObj).length > 0) ||
    (diagnosticObj && Object.keys(diagnosticObj).length > 0)
  ) {
    return {
      primary: {},
      secondary: secondaryObj || {},
      diagnostic: diagnosticObj || {},
      definitions: definitionsObj,
      scorecards: payload.scorecards ?? null,
      raw: payload,
    };
  }
  return {
    primary: {},
    secondary: {},
    diagnostic: {},
    definitions: null,
    scorecards: null,
    raw: payload,
  };
}
