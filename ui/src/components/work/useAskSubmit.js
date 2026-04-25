import { useCallback, useRef, useState } from "react";
import {
  formatResearchApiError,
  normalizeQueryResponse,
  postAgentQuery,
  postQuery,
} from "../../services/researchApi.js";
import { useAgentStream } from "../../hooks/useAgentStream.js";

/**
 * Orchestrates Ask submit flow: builds request, calls API, updates shell callbacks.
 *
 * @param {{
 *  workspaceId?: string,
 *  onResult?: (normalized: unknown) => void,
 *  onError?: (message: string) => void,
 *  onToolTrace?: (trace: unknown[]) => void,
 *  onStart?: () => void,
 *  onFinish?: () => void,
 *  onStreamEvent?: (event: unknown) => void,
 *  useStreamingAgent?: boolean
 * }} params
 */
export function useAskSubmit({
  workspaceId = "",
  onResult,
  onError,
  onToolTrace,
  onStart,
  onFinish,
  onStreamEvent,
  useStreamingAgent = true,
}) {
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef(null);

  const { stream: streamAgent, isStreaming, abort: abortStream } = useAgentStream({
    workspaceId,
    onEvent: (event) => {
      onStreamEvent?.(event);
    },
    onFinalAnswer: (event) => {
      const trace = Array.isArray(event?.tool_trace) ? event.tool_trace : [];
      onToolTrace?.(trace);
      const citations = Array.isArray(event?.citations) ? event.citations : [];
      const normalized = normalizeQueryResponse({
        answer: String(event?.answer || ""),
        citations,
        graph_context: {},
        retrieval_trace: {
          retrieval_mode: "agent_v2_stream",
          hit_count: citations.length,
          citations_returned: citations.length,
          retrieval_policy: "agent_tools_v2",
        },
      });
      onResult?.(normalized);
    },
    onError: (msg) => onError?.(msg),
    onStart: () => {
      setIsLoading(true);
      onStart?.();
    },
    onFinish: () => {
      setIsLoading(false);
      onFinish?.();
    },
  });

  const submit = useCallback(
    async ({ query, topK, retrievalMode, retrievalLabVisible, bodyPreview }) => {
      if (!String(query || "").trim()) return null;
      const isAgentMode = retrievalLabVisible && retrievalMode === "agent";

      if (isAgentMode && useStreamingAgent) {
        await streamAgent({ question: query, maxToolCalls: 8 });
        return null;
      }

      abortRef.current?.abort?.();
      abortStream();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsLoading(true);
      onStart?.();
      try {
        let normalized;
        let trace = [];

        if (isAgentMode) {
          const res = await postAgentQuery(
            {
              question: query,
              workspace_id: workspaceId || null,
              max_tool_calls: 8,
            },
            { signal: controller.signal },
          );
          const raw = res.data || {};
          trace = Array.isArray(raw.tool_trace) ? raw.tool_trace : [];
          normalized = normalizeQueryResponse({
            answer: String(raw.answer || ""),
            citations: Array.isArray(raw.citations) ? raw.citations : [],
            graph_context: {},
            retrieval_trace: {
              retrieval_mode: "agent",
              hit_count: Array.isArray(raw.citations) ? raw.citations.length : 0,
              top_k_requested: topK,
              citations_returned: Array.isArray(raw.citations) ? raw.citations.length : 0,
              retrieval_policy: "agent_tools_v1",
            },
          });
        } else {
          const res = await postQuery(bodyPreview, { signal: controller.signal });
          normalized = normalizeQueryResponse(res.data);
        }

        onToolTrace?.(trace);
        onResult?.(normalized);
        return normalized;
      } catch (err) {
        if (err?.name === "CanceledError" || err?.name === "AbortError") {
          return null;
        }
        onError?.(formatResearchApiError(err));
        return null;
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
        setIsLoading(false);
        onFinish?.();
      }
    },
    [
      abortStream,
      onError,
      onFinish,
      onResult,
      onStart,
      onToolTrace,
      streamAgent,
      useStreamingAgent,
      workspaceId,
    ],
  );

  const isActive = isLoading || isStreaming;

  return { submit, isLoading: isActive, abortRef };
}
