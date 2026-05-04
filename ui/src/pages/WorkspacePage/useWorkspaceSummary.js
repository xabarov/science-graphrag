import { useCallback, useState } from "react";

import { formatResearchApiError, postAgentQueryV2 } from "../../services/researchApi.js";

export function useWorkspaceSummary(workspaceId, t) {
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [summaryBusy, setSummaryBusy] = useState(false);
  const [summaryText, setSummaryText] = useState("");

  const handleSummarizeWorkspace = useCallback(async () => {
    const id = String(workspaceId || "").trim();
    if (!id) return;
    setSummaryBusy(true);
    try {
      const res = await postAgentQueryV2({
        question: t("workspace.summary.agentPrompt"),
        workspace_id: id,
        max_tool_calls: 8,
      });
      setSummaryText(String(res?.data?.answer || ""));
      setSummaryOpen(true);
    } catch (err) {
      setSummaryText(formatResearchApiError(err));
      setSummaryOpen(true);
    } finally {
      setSummaryBusy(false);
    }
  }, [workspaceId, t]);

  return {
    summaryOpen,
    setSummaryOpen,
    summaryBusy,
    summaryText,
    handleSummarizeWorkspace,
  };
}
