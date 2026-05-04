import { useCallback, useState } from "react";

import { formatResearchApiError, postIdeaAssist } from "../../services/researchApi.js";

export function useWorkspaceIdeaAssist(workspaceId, canUseIdeaAssist) {
  const [ideaOpen, setIdeaOpen] = useState(false);
  const [ideaBusy, setIdeaBusy] = useState(false);
  const [ideaError, setIdeaError] = useState("");
  const [ideaResult, setIdeaResult] = useState({ hypotheses: [], contradictions: [], toolTrace: [] });

  const handleGenerateHypotheses = useCallback(async () => {
    const id = String(workspaceId || "").trim();
    if (!id || !canUseIdeaAssist) return;
    setIdeaBusy(true);
    setIdeaError("");
    try {
      const res = await postIdeaAssist({
        workspace_id: id,
        mode: "both",
        max_candidates: 3,
      });
      const data = res?.data || {};
      setIdeaResult({
        hypotheses: Array.isArray(data.hypotheses) ? data.hypotheses : [],
        contradictions: Array.isArray(data.contradictions) ? data.contradictions : [],
        toolTrace: Array.isArray(data.tool_trace) ? data.tool_trace : [],
      });
      setIdeaOpen(true);
    } catch (err) {
      setIdeaResult({ hypotheses: [], contradictions: [], toolTrace: [] });
      setIdeaError(formatResearchApiError(err));
      setIdeaOpen(true);
    } finally {
      setIdeaBusy(false);
    }
  }, [workspaceId, canUseIdeaAssist]);

  return {
    ideaOpen,
    setIdeaOpen,
    ideaBusy,
    ideaError,
    ideaResult,
    handleGenerateHypotheses,
  };
}
