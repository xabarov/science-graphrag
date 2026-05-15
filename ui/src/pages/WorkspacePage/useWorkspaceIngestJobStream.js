import { useCallback } from "react";

import useJobStream from "../../hooks/useJobStream.js";
import { formatResearchApiError } from "../../services/researchApi.js";
import { setPersistedIngestJobId } from "./workspaceIngestStorage.js";

/**
 * Poll ingest job until terminal; refresh workspace and open dedup when needed.
 *
 * @param {{
 *   workspaceId: string,
 *   ingestJobId: string,
 *   setIngestJob: import("react").Dispatch<import("react").SetStateAction<unknown>>,
 *   setIngestJobId: import("react").Dispatch<import("react").SetStateAction<string>>,
 *   setIngestDedupPanelOpen: import("react").Dispatch<import("react").SetStateAction<boolean>>,
 *   refreshWorkspaceMeta: () => Promise<void>,
 *   setIngestErr: import("react").Dispatch<import("react").SetStateAction<unknown>>,
 * }} opts
 */
export function useWorkspaceIngestJobStream({
  workspaceId,
  ingestJobId,
  setIngestJob,
  setIngestJobId,
  setIngestDedupPanelOpen,
  refreshWorkspaceMeta,
  setIngestErr,
}) {
  useJobStream({
    jobId: ingestJobId,
    enabled: Boolean(ingestJobId),
    onUpdate: useCallback((job) => setIngestJob(job), [setIngestJob]),
    onTerminal: useCallback(
      async (job) => {
        await refreshWorkspaceMeta();
        const pc = job?.pending_conflicts;
        const pending =
          pc && typeof pc === "object"
            ? Number((pc.works || 0) + (pc.authors || 0) + (pc.entities || 0))
            : Number(job?.pending_conflicts_count || 0);
        if (String(job?.status || "") === "completed" && pending > 0) {
          setIngestDedupPanelOpen(true);
        }
        setPersistedIngestJobId(workspaceId, "");
        setIngestJobId("");
        setIngestJob(null);
      },
      [refreshWorkspaceMeta, workspaceId, setIngestDedupPanelOpen, setIngestJobId, setIngestJob],
    ),
    onError: useCallback(
      (err, failCount) => {
        if (failCount >= 3) setIngestErr(formatResearchApiError(err));
      },
      [setIngestErr],
    ),
    fallbackPollMs: 2000,
  });
}
