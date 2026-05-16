import { useCallback, useEffect, useRef, useState } from "react";

import { buildApiUrl } from "../services/apiClient.js";
import { consumeAgentSseReader } from "../services/agent/agentStreamConsume.js";
import { resumeAgentStream } from "../services/agent/agentStreamResume.js";

/** @typedef {'user_cancel' | 'replaced_by_new_request'} AgentStreamAbortReason */

/**
 * Streams POST /v2/agent/query (SSE). Callback props are read from refs so ``stream`` stays
 * stable when parent re-renders and only ``workspaceId`` should recreate the fetch function.
 *
 * **Abort contract:** When the browser raises `AbortError`, the hook distinguishes:
 * - **`user_cancel`** — consumer called ``abort()`` (intentional cancel).
 * - **`replaced_by_new_request`** — a new ``stream()`` started and aborted the previous fetch.
 * For these, **`onError` is not invoked** for the abort itself; use optional **`onAbort({ reason })`**
 * if you need telemetry or UI. Network and parse failures still go to **`onError`**.
 */
export function useAgentStream({
  workspaceId = "",
  onEvent,
  onFinalAnswer,
  onError,
  onAbort,
  onStart,
  onFinish,
  onMalformedFrame,
  onRunStarted,
  onSeq,
}) {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef(null);
  /** Why the in-flight fetch was aborted (set immediately before `abort()`). */
  const abortIntentRef = useRef(/** @type {AgentStreamAbortReason | null} */ (null));
  /** True after any `onFinalAnswer` delivery for the current stream (SSE or JSON). */
  const sawFinalAnswerRef = useRef(false);

  const cbRef = useRef({
    onEvent,
    onFinalAnswer,
    onError,
    onAbort,
    onStart,
    onFinish,
    onMalformedFrame,
    onRunStarted,
    onSeq,
  });
  useEffect(() => {
    cbRef.current = {
      onEvent,
      onFinalAnswer,
      onError,
      onAbort,
      onStart,
      onFinish,
      onMalformedFrame,
      onRunStarted,
      onSeq,
    };
  }, [onEvent, onFinalAnswer, onError, onAbort, onStart, onFinish, onMalformedFrame, onRunStarted, onSeq]);

  const stream = useCallback(
    async ({
      question,
      maxToolCalls = 8,
      threadId = null,
      historyDigest = null,
      clientIdleMs = null,
      userStructuredAnswer = null,
      pdfReadRequest = null,
      webResearchEnabled = false,
      agentMode = "agent",
    }) => {
      if (!String(question || "").trim()) return;

      if (abortRef.current) {
        abortIntentRef.current = "replaced_by_new_request";
        abortRef.current.abort();
      }
      const controller = new AbortController();
      abortRef.current = controller;

      setIsStreaming(true);
      sawFinalAnswerRef.current = false;
      cbRef.current.onStart?.();

      try {
        const response = await fetch(buildApiUrl("/v2/agent/query"), {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({
            question,
            workspace_id: workspaceId || null,
            max_tool_calls: maxToolCalls,
            thread_id: threadId || null,
            history_digest: historyDigest || null,
            web_research_enabled: webResearchEnabled,
            agent_mode: agentMode,
            ...(clientIdleMs != null && Number.isFinite(Number(clientIdleMs))
              ? { client_idle_ms: Math.max(0, Math.round(Number(clientIdleMs))) }
              : {}),
            ...(userStructuredAnswer && typeof userStructuredAnswer === "object"
              ? { user_structured_answer: userStructuredAnswer }
              : {}),
            ...(pdfReadRequest && typeof pdfReadRequest === "object"
              ? { pdf_read_request: pdfReadRequest }
              : {}),
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          const errText = await response.text().catch(() => "Unknown error");
          cbRef.current.onError?.(`Agent error ${response.status}: ${errText}`);
          return;
        }

        const contentType = String(response.headers?.get?.("content-type") || "");
        if (!contentType.includes("text/event-stream")) {
          const rawText = await response.text();
          try {
            const data = rawText ? JSON.parse(rawText) : {};
            sawFinalAnswerRef.current = true;
            cbRef.current.onFinalAnswer?.(data);
          } catch (parseErr) {
            cbRef.current.onError?.(
              `Agent response is not valid JSON: ${String(parseErr?.message || parseErr)}${rawText ? ` — ${rawText.slice(0, 200)}` : ""}`,
            );
          }
          return;
        }

        if (!response.body || typeof response.body.getReader !== "function") {
          cbRef.current.onError?.("Agent stream is unavailable in this browser");
          return;
        }

        const reader = response.body.getReader();
        const { sawFinalAnswer, streamEmittedError } = await consumeAgentSseReader(reader, {
          onEvent: (ev) => cbRef.current.onEvent?.(ev),
          onFinalAnswer: (ev) => {
            sawFinalAnswerRef.current = true;
            cbRef.current.onFinalAnswer?.(ev);
          },
          onError: (msg) => cbRef.current.onError?.(msg),
          onRunStarted: (ev) => cbRef.current.onRunStarted?.(ev),
          onParseError: (err) => cbRef.current.onMalformedFrame?.(err),
          onSeq: (seq) => cbRef.current.onSeq?.(seq),
        });
        sawFinalAnswerRef.current = sawFinalAnswer;

        if (!sawFinalAnswerRef.current && !controller.signal.aborted && !streamEmittedError) {
          cbRef.current.onError?.("Stream ended before a final answer was received.");
        }
      } catch (err) {
        if (err?.name === "AbortError") {
          const intent = abortIntentRef.current;
          abortIntentRef.current = null;
          if (intent === "user_cancel" || intent === "replaced_by_new_request") {
            cbRef.current.onAbort?.({ reason: intent });
          }
          return;
        }
        cbRef.current.onError?.(String(err?.message || err));
      } finally {
        const ownsAbortSlot = abortRef.current === controller;
        if (ownsAbortSlot) {
          abortRef.current = null;
        }
        abortIntentRef.current = null;
        // A newer `stream()` may have replaced `abortRef`; do not clear loading / onFinish for superseded runs.
        if (ownsAbortSlot) {
          setIsStreaming(false);
          cbRef.current.onFinish?.();
        }
      }
    },
    [workspaceId],
  );

  const resumeStream = useCallback(
    async ({ runId, afterSeq = 0 }) => {
      const rid = String(runId || "").trim();
      if (!rid) return;

      if (abortRef.current) {
        abortIntentRef.current = "replaced_by_new_request";
        abortRef.current.abort();
      }
      const controller = new AbortController();
      abortRef.current = controller;

      setIsStreaming(true);
      sawFinalAnswerRef.current = false;
      cbRef.current.onStart?.();

      try {
        const result = await resumeAgentStream({
          runId: rid,
          afterSeq,
          signal: controller.signal,
          onEvent: (ev) => cbRef.current.onEvent?.(ev),
          onFinalAnswer: (ev) => {
            sawFinalAnswerRef.current = true;
            cbRef.current.onFinalAnswer?.(ev);
          },
          onError: (msg) => cbRef.current.onError?.(msg),
          onRunStarted: (ev) => cbRef.current.onRunStarted?.(ev),
        });
        if (result?.lastSeq != null) {
          cbRef.current.onSeq?.(result.lastSeq);
        }
        if (!sawFinalAnswerRef.current && result?.sawFinalAnswer) {
          sawFinalAnswerRef.current = true;
        }
        // Resume is an idempotent reconnect: an empty/partial replay can happen when the
        // server-side run is still active or the client already consumed the buffered tail.
        // Do not turn that into a user-visible failed answer; the Ask layer keeps the
        // in-flight snapshot and can reconnect again.
      } catch (err) {
        if (err?.name === "AbortError") {
          const intent = abortIntentRef.current;
          abortIntentRef.current = null;
          if (intent === "user_cancel" || intent === "replaced_by_new_request") {
            cbRef.current.onAbort?.({ reason: intent });
          }
          return;
        }
        cbRef.current.onError?.(String(err?.message || err));
      } finally {
        const ownsAbortSlot = abortRef.current === controller;
        if (ownsAbortSlot) {
          abortRef.current = null;
        }
        abortIntentRef.current = null;
        if (ownsAbortSlot) {
          setIsStreaming(false);
          cbRef.current.onFinish?.();
        }
      }
    },
    [],
  );

  const abort = useCallback(() => {
    abortIntentRef.current = "user_cancel";
    abortRef.current?.abort?.();
  }, []);

  return { stream, resumeStream, isStreaming, abort };
}
