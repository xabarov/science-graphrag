import { useEffect, useState } from "react";

import { getWorkspaceContradictionDetail } from "../../../../utils/workspaceStore.js";

/**
 * Loads contradiction detail when a CONTRADICTS edge is selected in a workspace context.
 */
export function useGraphContradictionDetail({ effectiveWorkspaceId, isContradictsEdge, selectedEdge, t }) {
  const [contradictionPayload, setContradictionPayload] = useState(/** @type {Record<string, unknown> | null} */ (null));
  const [contradictionBusy, setContradictionBusy] = useState(false);
  const [contradictionError, setContradictionError] = useState("");

  /* eslint-disable react-hooks/exhaustive-deps -- stable edge id/source/target; full selectedEdge changes identity each graph normalize */
  useEffect(() => {
    if (!isContradictsEdge || !effectiveWorkspaceId || !selectedEdge) {
      setContradictionPayload(null);
      setContradictionError("");
      setContradictionBusy(false);
      return;
    }
    const src = String(selectedEdge.source || "").trim();
    const tgt = String(selectedEdge.target || "").trim();
    if (!src || !tgt) {
      setContradictionPayload(null);
      return;
    }
    let cancelled = false;
    setContradictionBusy(true);
    setContradictionError("");
    (async () => {
      try {
        const data = await getWorkspaceContradictionDetail(effectiveWorkspaceId, src, tgt);
        if (!cancelled) setContradictionPayload(data && typeof data === "object" ? data : null);
      } catch {
        if (!cancelled) {
          setContradictionPayload(null);
          setContradictionError(t("graph.detailPanel.contradictionDetailError"));
        }
      } finally {
        if (!cancelled) setContradictionBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [effectiveWorkspaceId, isContradictsEdge, selectedEdge?.id, selectedEdge?.source, selectedEdge?.target, t]);
  /* eslint-enable react-hooks/exhaustive-deps */

  return { contradictionPayload, contradictionBusy, contradictionError };
}
