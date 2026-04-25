import { useCallback, useRef, useState } from "react";
import {
  formatResearchApiError,
  normalizeQueryResponse,
  postAgentQuery,
  postQuery,
} from "../../services/researchApi.js";

/**
 * Orchestrates Ask submit flow: builds request, calls API, updates shell callbacks.
 *
 * @param {{
 *  workspaceId?: string,
 *  onResult?: (normalized: unknown) => void,
 *  onError?: (message: string) => void,
 *  onToolTrace?: (trace: unknown[]) => void,
 *  onStart?: () => void,
 *  onFinish?: () => void
 * }} params
 */
export function useAskSubmit({ workspaceId = "", onResult, onError, onToolTrace, onStart, onFinish }) {
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef(null);

  const submit = useCallback(
    async ({ query, topK, retrievalMode, retrievalLabVisible, bodyPreview }) => {
      if (!String(query || "").trim()) return null;

      abortRef.current?.abort?.();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsLoading(true);
      onStart?.();
      try {
        let normalized;
        let trace = [];

        if (retrievalLabVisible && retrievalMode === "agent") {
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
    [onError, onFinish, onResult, onStart, onToolTrace, workspaceId],
  );

  return { submit, isLoading, abortRef };
}
