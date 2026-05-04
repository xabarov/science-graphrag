import { useEffect } from "react";

import {
  getWorkspaceAuthorDedupConflicts,
  getWorkspaceSmartDedupConflicts,
  listEntityDedupConflicts,
} from "../../utils/workspaceStore.js";

/**
 * When pending ingest-origin dedup conflicts exist, open the side panel once.
 */
export function useIngestDedupAutoOpen(workspaceId, setIngestDedupPanelOpen) {
  useEffect(() => {
    const id = String(workspaceId || "").trim();
    if (!id) {
      setIngestDedupPanelOpen(false);
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const entityTypes = ["institution", "venue", "method", "dataset"];
        const [wdata, adata, ...edatas] = await Promise.all([
          getWorkspaceSmartDedupConflicts(id, { status: "pending", origin: "ingest", limit: 1 }),
          getWorkspaceAuthorDedupConflicts(id, { status: "pending", origin: "ingest", limit: 1 }),
          ...entityTypes.map((entityType) =>
            listEntityDedupConflicts({
              entityType,
              workspaceId: id,
              origin: "ingest",
              status: "pending",
              limit: 1,
            }),
          ),
        ]);
        const hasWork = Array.isArray(wdata?.items) && wdata.items.length > 0;
        const hasAuthor = Array.isArray(adata?.items) && adata.items.length > 0;
        const hasEntity = edatas.some((d) => Array.isArray(d?.items) && d.items.length > 0);
        if (!cancelled && (hasWork || hasAuthor || hasEntity)) {
          setIngestDedupPanelOpen(true);
        }
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workspaceId, setIngestDedupPanelOpen]);
}
