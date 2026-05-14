import { LS_GRAPH_STANDALONE_DETAIL_MIN_PX, readGraphDetailColumnPxStored } from "../model/graphDetailColumnWidth.js";

export const LS_GRAPH_CANVAS_LAYOUT_MODE = "graphCanvasLayoutMode";
export const LS_GRAPH_VIZ_MODE = "graphVizMode";
export const LS_STANDALONE_DETAILS = "graphStandaloneDetailsVisible";
export const LS_STANDALONE_LEGEND = "graphStandaloneLegendOpen";
export const LS_EMBEDDED_LEGEND = "graphEmbeddedLegendOpen";
export const LS_GRAPH_CANVAS_COLOR_BY = "graphCanvasColorBy";
export const LS_GRAPH_CANVAS_COMMUNITY_HULLS = "graphCanvasCommunityHulls";

export { LS_GRAPH_STANDALONE_DETAIL_MIN_PX, readGraphDetailColumnPxStored };

export function readLsMode() {
  if (typeof window === "undefined") return "canvas";
  try {
    const v = window.localStorage.getItem(LS_GRAPH_VIZ_MODE);
    return v === "cards" || v === "canvas" || v === "flow" ? v : "canvas";
  } catch {
    return "canvas";
  }
}

export function readLsLayout() {
  if (typeof window === "undefined") return "force";
  try {
    return window.localStorage.getItem(LS_GRAPH_CANVAS_LAYOUT_MODE) === "circle" ? "circle" : "force";
  } catch {
    return "force";
  }
}

export function readBoolLs(key, fallback) {
  if (typeof window === "undefined") return fallback;
  try {
    const v = window.localStorage.getItem(key);
    if (v == null) return fallback;
    return v === "1";
  } catch {
    return fallback;
  }
}

/** @returns {"type" | "community"} */
export function readGraphColorByStored() {
  if (typeof window === "undefined") return "type";
  try {
    const v = window.localStorage.getItem(LS_GRAPH_CANVAS_COLOR_BY);
    if (v === "type" || v === "community") return v;
  } catch {
    /* ignore */
  }
  return "type";
}
