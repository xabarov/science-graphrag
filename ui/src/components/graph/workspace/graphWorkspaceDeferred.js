/**
 * Yield to the browser so the first normalized graph can paint before aggregator prefetch.
 * @returns {Promise<void>}
 */
export function scheduleDeferredGraphPrefetch() {
  return new Promise((resolve) => {
    if (typeof requestIdleCallback === "function") {
      requestIdleCallback(() => resolve(), { timeout: 450 });
    } else {
      requestAnimationFrame(() => resolve());
    }
  });
}
