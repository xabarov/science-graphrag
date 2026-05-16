import { buildApiUrl } from "../apiClient.js";
import { consumeAgentSseReader } from "./agentStreamConsume.js";

/**
 * Resume buffered agent SSE run (GET /v2/agent/query/runs/{run_id}/stream).
 *
 * @param {{
 *   runId: string,
 *   afterSeq?: number,
 *   signal?: AbortSignal,
 *   onEvent?: (event: Record<string, unknown>) => void,
 *   onFinalAnswer?: (event: Record<string, unknown>) => void,
 *   onError?: (message: string) => void,
 *   onRunStarted?: (event: Record<string, unknown>) => void,
 * }} params
 */
export async function resumeAgentStream({
  runId,
  afterSeq = 0,
  signal,
  onEvent,
  onFinalAnswer,
  onError,
  onRunStarted,
}) {
  const rid = String(runId || "").trim();
  if (!rid) {
    onError?.("Missing run id for resume");
    return;
  }
  if (!rid.startsWith("run-")) {
    return { lastSeq: Math.max(0, Number(afterSeq) || 0), sawFinalAnswer: false };
  }
  const startSeq = Math.max(0, Number(afterSeq) || 0);

  async function runResumePass(seqBase) {
    const url = buildApiUrl(
      `/v2/agent/query/runs/${encodeURIComponent(rid)}/stream?after_seq=${Math.max(0, Number(seqBase) || 0)}`,
    );
    const response = await fetch(url, {
      method: "GET",
      headers: { Accept: "text/event-stream" },
      signal,
    });
    if (!response.ok) {
      const errText = await response.text().catch(() => "Unknown error");
      onError?.(`Resume error ${response.status}: ${errText}`);
      return null;
    }
    if (!response.body?.getReader) {
      onError?.("Resume stream unavailable in this browser");
      return null;
    }
    const reader = response.body.getReader();
    let lastSeq = Math.max(0, Number(seqBase) || 0);
    const result = await consumeAgentSseReader(reader, {
      onEvent: (ev) => onEvent?.(ev),
      onFinalAnswer: (ev) => onFinalAnswer?.(ev),
      onError: (msg) => onError?.(msg),
      onRunStarted: (ev) => onRunStarted?.(ev),
      onSeq: (seq) => {
        lastSeq = Math.max(lastSeq, seq);
      },
    });
    return {
      lastSeq: Math.max(lastSeq, result.lastSeq),
      sawFinalAnswer: result.sawFinalAnswer,
      streamEmittedError: result.streamEmittedError,
    };
  }

  const first = await runResumePass(startSeq);
  if (!first) return { lastSeq: startSeq, sawFinalAnswer: false };
  if (first.sawFinalAnswer || first.streamEmittedError || signal?.aborted) {
    return { lastSeq: first.lastSeq, sawFinalAnswer: first.sawFinalAnswer };
  }
  // Idempotent resume can race with already-drained buffer state. Re-fetch full replay once.
  if (startSeq > 0 && first.lastSeq <= startSeq) {
    const replay = await runResumePass(0);
    if (replay) {
      return {
        lastSeq: Math.max(first.lastSeq, replay.lastSeq),
        sawFinalAnswer: replay.sawFinalAnswer || first.sawFinalAnswer,
      };
    }
  }
  return { lastSeq: first.lastSeq, sawFinalAnswer: first.sawFinalAnswer };
}
