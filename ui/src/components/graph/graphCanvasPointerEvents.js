/** Dispatched when the graph canvas receives primary-button pointer down (before hit-test). */
export const GRAPH_CANVAS_POINTER_DOWN_EVENT = "science-graphrag:graph-canvas-pointer-down";

/** Dispatched when the graph canvas pointer interaction ends (up/cancel). */
export const GRAPH_CANVAS_POINTER_UP_EVENT = "science-graphrag:graph-canvas-pointer-up";

/**
 * @param {EventTarget | null | undefined} [target] Defaults to `window` in the browser.
 */
export function dispatchGraphCanvasPointerDown(target) {
  const t = target ?? (typeof window !== "undefined" ? window : null);
  if (!t) return;
  t.dispatchEvent(new CustomEvent(GRAPH_CANVAS_POINTER_DOWN_EVENT));
}

/**
 * @param {EventTarget | null | undefined} [target] Defaults to `window` in the browser.
 */
export function dispatchGraphCanvasPointerUp(target) {
  const t = target ?? (typeof window !== "undefined" ? window : null);
  if (!t) return;
  t.dispatchEvent(new CustomEvent(GRAPH_CANVAS_POINTER_UP_EVENT));
}
