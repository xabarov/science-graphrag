/** Standalone graph/detail split: shared bounds for slider and drag-resize gutter. */

export const GRAPH_DETAIL_COLUMN_PX_MIN = 260;
export const GRAPH_DETAIL_COLUMN_PX_MAX = 480;
export const GRAPH_DETAIL_COLUMN_PX_STEP = 20;

export const LS_GRAPH_STANDALONE_DETAIL_MIN_PX = "graphStandaloneDetailMinPx";

/**
 * @param {number} n
 * @returns {number}
 */
export function clampGraphDetailColumnPx(n) {
  if (!Number.isFinite(n)) return 320;
  return Math.min(
    GRAPH_DETAIL_COLUMN_PX_MAX,
    Math.max(GRAPH_DETAIL_COLUMN_PX_MIN, Math.round(n)),
  );
}

/**
 * @returns {number}
 */
export function readGraphDetailColumnPxStored() {
  if (typeof window === "undefined") return 320;
  try {
    const raw = window.localStorage.getItem(LS_GRAPH_STANDALONE_DETAIL_MIN_PX);
    const parsed = raw == null ? NaN : parseInt(raw, 10);
    if (!Number.isFinite(parsed)) return 320;
    return clampGraphDetailColumnPx(parsed);
  } catch {
    return 320;
  }
}
