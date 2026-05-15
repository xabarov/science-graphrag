import { startTransition, useEffect, useState } from "react";

import { getWorkspaceGraphStats } from "../../utils/workspaceStore.js";

/**
 * Load workspace graph stats when workspace id or work list changes.
 *
 * @param {string} workspaceId
 * @param {unknown} workIdsDependency workspaceMeta.work_ids (array identity from API)
 * @returns {Record<string, unknown> | null}
 */
export function useWorkspaceGraphStats(workspaceId, workIdsDependency) {
  const [graphStats, setGraphStats] = useState(null);

  useEffect(() => {
    const id = String(workspaceId || "").trim();
    if (!id) {
      startTransition(() => {
        setGraphStats(null);
      });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const s = await getWorkspaceGraphStats(id);
        if (!cancelled) setGraphStats(s);
      } catch {
        if (!cancelled) setGraphStats(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workspaceId, workIdsDependency]);

  return graphStats;
}
