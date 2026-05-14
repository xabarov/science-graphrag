/**
 * Attach client receive time for live headline freshness (e.g. stale product_step window).
 *
 * @param {unknown} event
 * @returns {unknown}
 */
export function withStreamEventReceiveTime(event) {
  if (!event || typeof event !== "object") return event;
  return { .../** @type {Record<string, unknown>} */ (event), _receivedAtMs: Date.now() };
}
