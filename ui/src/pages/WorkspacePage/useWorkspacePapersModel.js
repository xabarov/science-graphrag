import { useEffect, useMemo, useState } from "react";

import { formatResearchApiError, getWorkDetail } from "../../services/researchApi.js";
import { rememberRecentWork } from "../HomePage/homeState.js";

/**
 * Loads per-work metadata for all works in the current workspace list.
 * @param {{ workspaceId: string, effectiveWorkIds: string[] }} params
 */
export function useWorkspacePapersModel({ workspaceId, effectiveWorkIds }) {
  const [papers, setPapers] = useState(() => new Map());
  const workIdsKey = useMemo(() => effectiveWorkIds.join("|"), [effectiveWorkIds]);

  useEffect(() => {
    if (!effectiveWorkIds.length) return undefined;
    let cancelled = false;
    (async () => {
      for (const wid of effectiveWorkIds) {
        setPapers((prev) => {
          const m = new Map(prev);
          const cur = m.get(wid) || {};
          m.set(wid, { ...cur, workId: wid, loading: true, error: null });
          return m;
        });
        try {
          const res = await getWorkDetail(wid);
          if (cancelled) return;
          const d = res.data;
          setPapers((prev) => {
            const m = new Map(prev);
            m.set(wid, {
              workId: wid,
              title: typeof d?.title === "string" ? d.title : "",
              year: d?.year ?? null,
              doi: d?.doi ?? null,
              arxivId: d?.arxiv_id ?? null,
              loading: false,
              error: null,
            });
            return m;
          });
          rememberRecentWork({
            workId: wid,
            title: typeof d?.title === "string" ? d.title : "",
            year: d?.year ?? null,
            tab: "overview",
            workspaceId: workspaceId || "",
          });
        } catch (err) {
          if (cancelled) return;
          setPapers((prev) => {
            const m = new Map(prev);
            m.set(wid, {
              workId: wid,
              title: "",
              loading: false,
              error: formatResearchApiError(err),
            });
            return m;
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workIdsKey, effectiveWorkIds, workspaceId]);

  return { papers };
}
