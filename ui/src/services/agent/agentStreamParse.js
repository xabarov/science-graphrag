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

/**
 * Flush complete SSE frames from a text buffer (split on `\n\n`).
 * @param {string} buffer
 * @param {{
 *   onEvent?: (event: Record<string, unknown>) => void,
 *   onFinalAnswer?: (event: Record<string, unknown>) => void,
 *   onError?: (message: string) => void,
 *   onParseError?: (err: unknown) => void,
 * }} handlers
 * @returns {string} trailing incomplete buffer
 */
/** SSE frame delimiter: LF LF (some servers) or CRLF CRLF (sse_starlette default). */
const SSE_FRAME_SPLIT = /\r?\n\r?\n/;

export function flushAgentSseEventBuffer(buffer, handlers = {}) {
  const { onEvent, onFinalAnswer, onError, onParseError } = handlers;
  const frames = buffer.split(SSE_FRAME_SPLIT);
  const nextBuffer = frames.pop() ?? "";

  for (const frame of frames) {
    if (!String(frame).trim()) continue;
    const lines = frame.split(/\r?\n/);
    const dataLines = lines
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim())
      .filter(Boolean);
    if (dataLines.length === 0) continue;

    const raw = dataLines.join("\n");
    const event = parseAgentSseJson(raw, { onParseError });
    if (!event || typeof event !== "object") continue;
    onEvent?.(event);
    if (event.type === "final_answer") {
      onFinalAnswer?.(event);
    } else if (event.type === "error") {
      onError?.(String(event.detail || event.error || "Stream error"));
    }
  }

  return nextBuffer;
}
