import { useCallback, useEffect, useMemo } from "react";

import { persistWorkId, resolveSelectedWorkId } from "./utils/workContext.js";

/**
 * Resolves selected work from URL + workspace meta and keeps URL/local persistence in sync.
 */
export function useWorkspacePageWorkSelection({
  workspaceMeta,
  workIdFromUrl,
  setSearchParams,
}) {
  const effectiveWorkIds = useMemo(() => {
    const fromWs = Array.isArray(workspaceMeta.work_ids) ? workspaceMeta.work_ids : [];
    if (fromWs.length) return fromWs;
    return [];
  }, [workspaceMeta.work_ids]);

  const selectedWorkId = useMemo(
    () => resolveSelectedWorkId({ workIds: effectiveWorkIds, workIdFromUrl }),
    [effectiveWorkIds, workIdFromUrl],
  );

  const setWorkFocusInUrl = useCallback(
    (wid) => {
      const w = String(wid || "").trim();
      if (!workspaceMeta.id || !w) return;
      const p = new URLSearchParams();
      p.set("workspace_id", workspaceMeta.id);
      p.set("work_id", w);
      setSearchParams(p, { replace: true });
    },
    [workspaceMeta.id, setSearchParams],
  );

  useEffect(() => {
    if (selectedWorkId) persistWorkId(selectedWorkId);
  }, [selectedWorkId]);

  const onCardActivate =
    workspaceMeta.id && effectiveWorkIds.length > 1 ? (wid) => setWorkFocusInUrl(wid) : undefined;

  return {
    effectiveWorkIds,
    selectedWorkId,
    setWorkFocusInUrl,
    onCardActivate,
  };
}
