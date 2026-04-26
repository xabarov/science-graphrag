/**
 * Parse one SSE `data:` JSON payload from the agent v2 stream.
 * @param {string} raw
 * @param {{ onParseError?: (err: unknown) => void }} [opts]
 * @returns {Record<string, unknown> | null}
 */
export function parseAgentSseJson(raw, opts = {}) {
  try {
    return JSON.parse(raw);
  } catch (err) {
    opts.onParseError?.(err);
    return null;
  }
}
