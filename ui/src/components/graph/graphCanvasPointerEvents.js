/** Dispatched when the graph canvas receives primary-button pointer down (before hit-test). */
export const GRAPH_CANVAS_POINTER_DOWN_EVENT = "science-graphrag:graph-canvas-pointer-down";

/** Dispatched when the graph canvas pointer interaction ends (up/cancel). */
export const GRAPH_CANVAS_POINTER_UP_EVENT = "science-graphrag:graph-canvas-pointer-up";

export function dispatchGraphCanvasPointerDown() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(GRAPH_CANVAS_POINTER_DOWN_EVENT));
}

export function dispatchGraphCanvasPointerUp() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(GRAPH_CANVAS_POINTER_UP_EVENT));
}
