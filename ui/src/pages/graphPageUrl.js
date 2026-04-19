/**
 * Standalone /graph URL helpers (layout flags, preserving params on work_id submit).
 */

/** @param {URLSearchParams} searchParams */
export function readGraphPageLayoutFlags(searchParams) {
  const compact = searchParams.get("compact") === "1";
  const focus = searchParams.get("focus") === "1";
  return {
    compact,
    focus,
    /** Denser graph panel defaults; `focus` implies this as well. */
    compactLayout: compact || focus,
  };
}

/**
 * Copy optional graph layout/lab flags from the previous query into `params`.
 * @param {URLSearchParams} params
 * @param {URLSearchParams} prev
 */
export function preserveGraphPageOptionalParams(params, prev) {
  if (prev.get("lab") === "1") params.set("lab", "1");
  if (prev.get("compact") === "1") params.set("compact", "1");
  if (prev.get("focus") === "1") params.set("focus", "1");
  const ws = prev.get("workspace_id");
  if (ws && String(ws).trim()) params.set("workspace_id", String(ws).trim());
}
