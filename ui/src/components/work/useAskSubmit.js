import { useCallback, useEffect, useRef, useState } from "react";
import { formatResearchApiError, normalizeQueryResponse, postAgentQuery } from "../../services/researchApi.js";
import { useAgentStream } from "../../hooks/useAgentStream.js";

/**
 * Orchestrates chat submit: streaming agent only (no vector/hybrid UI path).
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
  /** Last normalized payload produced by streaming agent (submit returns it after stream ends). */
  const lastStreamNormalizedRef = useRef(null);

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
        answer_class: event?.answer_class,
        evidence_summary: event?.evidence_summary,
        warnings: event?.warnings,
        inventory: event?.inventory,
        relation_trace: event?.relation_trace,
        quote_candidates: event?.quote_candidates,
        idea_suggestions: event?.idea_suggestions,
        bibliography: event?.bibliography,
      });
      lastStreamNormalizedRef.current = normalized;
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

  useEffect(() => {
    lastStreamNormalizedRef.current = null;
  }, [workspaceId]);

  const submit = useCallback(
    async ({ query }) => {
      if (!String(query || "").trim()) return null;

      if (useStreamingAgent) {
        lastStreamNormalizedRef.current = null;
        await streamAgent({ question: query, maxToolCalls: 8 });
        return lastStreamNormalizedRef.current;
      }

      abortRef.current?.abort?.();
      abortStream();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsLoading(true);
      onStart?.();
      try {
        const res = await postAgentQuery(
          {
            question: query,
            workspace_id: workspaceId || null,
            max_tool_calls: 8,
          },
          { signal: controller.signal },
        );
        const raw = res.data || {};
        const trace = Array.isArray(raw.tool_trace) ? raw.tool_trace : [];
        const normalized = normalizeQueryResponse({
          answer: String(raw.answer || ""),
          citations: Array.isArray(raw.citations) ? raw.citations : [],
          graph_context: {},
          retrieval_trace: {
            retrieval_mode: "agent",
            hit_count: Array.isArray(raw.citations) ? raw.citations.length : 0,
            citations_returned: Array.isArray(raw.citations) ? raw.citations.length : 0,
            retrieval_policy: "agent_tools_v1",
          },
        });
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
    [abortStream, onError, onFinish, onResult, onStart, onToolTrace, streamAgent, useStreamingAgent, workspaceId],
  );

  const isActive = isLoading || isStreaming;

  return { submit, isLoading: isActive, abortRef };
}
