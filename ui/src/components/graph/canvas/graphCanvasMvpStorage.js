import { REPULSION_DEFAULT_PERCENT } from "./physics/simConstants.js";

export const LS_GRAPH_CANVAS_REPULSION = "graphCanvasRepulsionPercent";
export const LS_GRAPH_DENSE_LABEL_HINT_DISMISSED = "graphDenseLabelHintDismissed";

export function readRepulsionPercentStored() {
  if (typeof window === "undefined") return REPULSION_DEFAULT_PERCENT;
  try {
    const raw = window.localStorage.getItem(LS_GRAPH_CANVAS_REPULSION);
    if (raw == null || raw === "") return REPULSION_DEFAULT_PERCENT;
    const n = Number(raw);
    if (!Number.isFinite(n)) return REPULSION_DEFAULT_PERCENT;
    return Math.min(100, Math.max(0, n));
  } catch {
    return REPULSION_DEFAULT_PERCENT;
  }
}

export function persistRepulsionPercent(pct) {
  try {
    window.localStorage.setItem(LS_GRAPH_CANVAS_REPULSION, String(pct));
  } catch {
    /* ignore */
  }
}

export function readDenseLabelHintDismissed() {
  if (typeof window === "undefined") return false;
  try {
    return window.sessionStorage.getItem(LS_GRAPH_DENSE_LABEL_HINT_DISMISSED) === "1";
  } catch {
    return false;
  }
}

export function persistDenseLabelHintDismissed() {
  try {
    window.sessionStorage.setItem(LS_GRAPH_DENSE_LABEL_HINT_DISMISSED, "1");
  } catch {
    /* ignore */
  }
}
