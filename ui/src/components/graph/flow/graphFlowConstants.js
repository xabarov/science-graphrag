/** Minimum height for the React Flow viewport region. */
export const GRAPH_FLOW_MIN_VIEW_HEIGHT = 280;

export const LS_GRAPH_FLOW_MINIMAP = "graphFlowMinimap";

export function readGraphFlowMinimapPreference() {
  if (typeof window === "undefined") return true;
  try {
    const v = window.localStorage.getItem(LS_GRAPH_FLOW_MINIMAP);
    if (v === null) return true;
    return v === "1";
  } catch {
    return true;
  }
}
