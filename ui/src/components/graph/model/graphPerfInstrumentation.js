/**
 * Opt-in Performance marks/measures for workspace graph projection (main thread).
 * Enable: localStorage `science-graphrag:graphPerf=1` (same pattern as graphTelemetry).
 */

const LS_GRAPH_PERF = "science-graphrag:graphPerf";

let measureSeq = 0;

/**
 * @returns {boolean}
 */
export function isGraphPerfMarksEnabled() {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage?.getItem(LS_GRAPH_PERF) === "1";
  } catch {
    return false;
  }
}

/**
 * Runs `fn` and records a Performance measure when perf marks are enabled.
 * Start/end marks are cleared after each measure to avoid unbounded mark growth during long sessions.
 *
 * @template T
 * @param {string} label Logical stage name (repeated measures share this label for filtering).
 * @param {() => T} fn
 * @returns {T}
 */
export function measureGraphStage(label, fn) {
  if (!isGraphPerfMarksEnabled() || typeof performance === "undefined" || typeof performance.mark !== "function") {
    return fn();
  }
  const id = ++measureSeq;
  const start = `${label}-s-${id}`;
  const end = `${label}-e-${id}`;
  performance.mark(start);
  try {
    return fn();
  } finally {
    performance.mark(end);
    try {
      performance.measure(label, start, end);
    } catch {
      /* duplicate / cleared marks in fast rerenders */
    }
    try {
      performance.clearMarks(start);
      performance.clearMarks(end);
    } catch {
      /* non-browser or restricted performance API */
    }
  }
}
