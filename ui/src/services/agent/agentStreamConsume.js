import { flushAgentSseEventBuffer } from "./agentStreamParse.js";

/**
 * Read an SSE response body and dispatch parsed agent events.
 *
 * @param {ReadableStreamDefaultReader<Uint8Array>} reader
 * @param {{
 *   onEvent?: (event: Record<string, unknown>) => void,
 *   onFinalAnswer?: (event: Record<string, unknown>) => void,
 *   onError?: (message: string) => void,
 *   onRunStarted?: (event: Record<string, unknown>) => void,
 *   onParseError?: (err: unknown) => void,
 *   onSeq?: (seq: number) => void,
 * }} handlers
 * @returns {Promise<{ lastSeq: number, sawFinalAnswer: boolean, streamEmittedError: boolean }>}
 */
export async function consumeAgentSseReader(reader, handlers = {}) {
  const decoder = new TextDecoder();
  let buffer = "";
  let lastSeq = 0;
  let sawFinalAnswer = false;
  let streamEmittedError = false;

  const sseHandlers = {
    onEvent: (ev) => {
      if (ev?.type === "run_started") {
        handlers.onRunStarted?.(ev);
        return;
      }
      handlers.onEvent?.(ev);
    },
    onFinalAnswer: (ev) => {
      sawFinalAnswer = true;
      handlers.onFinalAnswer?.(ev);
    },
    onError: (msg) => {
      if (sawFinalAnswer) return;
      streamEmittedError = true;
      handlers.onError?.(msg);
    },
    onParseError: handlers.onParseError,
  };

  const processFrame = (frame) => {
    if (!String(frame).trim()) return;
    const lines = frame.split(/\r?\n/);
    for (const line of lines) {
      if (line.startsWith("id:")) {
        const n = Number(line.slice(3).trim());
        if (Number.isFinite(n) && n > lastSeq) {
          lastSeq = n;
          handlers.onSeq?.(n);
        }
      }
    }
    flushAgentSseEventBuffer(frame.endsWith("\n\n") ? frame : `${frame}\n\n`, sseHandlers);
  };

  let done = false;
  while (!done) {
    const chunk = await reader.read();
    done = Boolean(chunk.done);
    if (done) break;
    const value = chunk.value;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split(/\r?\n\r?\n/);
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      processFrame(frame);
    }
  }
  buffer += decoder.decode();
  if (buffer.trim()) {
    processFrame(buffer);
  }
  return { lastSeq, sawFinalAnswer, streamEmittedError };
}
