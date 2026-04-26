import { useCallback, useRef, useState } from "react";

import { buildApiUrl } from "../services/apiClient.js";
import { parseAgentSseJson } from "../services/agent/agentStreamParse.js";

function flushSseBuffer(buffer, onEvent, onFinalAnswer, onError, onParseError) {
  const frames = buffer.split("\n\n");
  const nextBuffer = frames.pop() ?? "";

  for (const frame of frames) {
    const lines = frame.split("\n");
    const dataLines = lines
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim())
      .filter(Boolean);
    if (dataLines.length === 0) continue;

    const raw = dataLines.join("\n");
    const event = parseAgentSseJson(raw, { onParseError });
    if (!event || typeof event !== "object") continue;
    onEvent?.(event);
    if (event?.type === "final_answer") {
      onFinalAnswer?.(event);
    } else if (event?.type === "error") {
      onError?.(event?.detail || event?.error || "Stream error");
    }
  }

  return nextBuffer;
}

export function useAgentStream({
  workspaceId = "",
  onEvent,
  onFinalAnswer,
  onError,
  onStart,
  onFinish,
  onMalformedFrame,
}) {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef(null);

  const stream = useCallback(
    async ({ question, maxToolCalls = 8, answerClassHint = null, threadId = null, historyDigest = null }) => {
      if (!String(question || "").trim()) return;

      abortRef.current?.abort?.();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsStreaming(true);
      onStart?.();

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
            answer_class_hint: answerClassHint || null,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          const errText = await response.text().catch(() => "Unknown error");
          onError?.(`Agent error ${response.status}: ${errText}`);
          return;
        }

        const contentType = String(response.headers?.get?.("content-type") || "");
        if (!contentType.includes("text/event-stream")) {
          const data = await response.json();
          onFinalAnswer?.(data);
          return;
        }

        if (!response.body || typeof response.body.getReader !== "function") {
          onError?.("Agent stream is unavailable in this browser");
          return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        let keepReading = true;
        while (keepReading) {
          const { done, value } = await reader.read();
          if (done) {
            keepReading = false;
            continue;
          }
          buffer += decoder.decode(value, { stream: true });
          buffer = flushSseBuffer(buffer, onEvent, onFinalAnswer, onError, onMalformedFrame);
        }

        buffer += decoder.decode();
        flushSseBuffer(buffer, onEvent, onFinalAnswer, onError, onMalformedFrame);
      } catch (err) {
        if (err?.name === "AbortError") return;
        onError?.(String(err?.message || err));
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
        setIsStreaming(false);
        onFinish?.();
      }
    },
    [workspaceId, onEvent, onFinalAnswer, onError, onStart, onFinish, onMalformedFrame],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort?.();
  }, []);

  return { stream, isStreaming, abort };
}
