import { useEffect, useMemo, useState } from "react";

import { formatResearchApiError, postWorksBatchSummary } from "../../services/researchApi.js";

const BATCH_MAX = 2000;

/**
 * Loads per-work metadata for all works in the current workspace list.
 * Uses POST /v1/works/batch-summary (one Neo4j round-trip per chunk) instead of N× GET /v1/works/{id}.
 *
 * @param {{ effectiveWorkIds: string[] }} params
 */
export function useWorkspacePapersModel({ effectiveWorkIds }) {
  const [papers, setPapers] = useState(() => new Map());
  const workIdsKey = useMemo(() => effectiveWorkIds.join("|"), [effectiveWorkIds]);

  useEffect(() => {
    if (!effectiveWorkIds.length) return undefined;
    let cancelled = false;

    const seen = new Set();
    const ids = [];
    for (const w of effectiveWorkIds) {
      const wid = String(w || "").trim();
      if (!wid || seen.has(wid)) continue;
      seen.add(wid);
      ids.push(wid);
    }

    queueMicrotask(() => {
      if (cancelled) return;
      setPapers((prev) => {
        const m = new Map(prev);
        for (const wid of ids) {
          const cur = m.get(wid) || {};
          m.set(wid, { ...cur, workId: wid, loading: true, error: null });
        }
        return m;
      });
    });

    (async () => {
      try {
        const byId = new Map();
        for (let i = 0; i < ids.length; i += BATCH_MAX) {
          const chunk = ids.slice(i, i + BATCH_MAX);
          const res = await postWorksBatchSummary(chunk);
          if (cancelled) return;
          const items = Array.isArray(res?.data?.items) ? res.data.items : [];
          for (const row of items) {
            const wid = String(row?.work_id || "").trim();
            if (!wid) continue;
            byId.set(wid, row);
          }
        }
        if (cancelled) return;
        setPapers((prev) => {
          const m = new Map(prev);
          for (const wid of ids) {
            const row = byId.get(wid);
            m.set(wid, {
              workId: wid,
              title: typeof row?.title === "string" ? row.title : "",
              year: row?.year ?? null,
              doi: row?.doi ?? null,
              arxivId: row?.arxiv_id ?? null,
              loading: false,
              error: null,
            });
          }
          return m;
        });
      } catch (err) {
        if (cancelled) return;
        const msg = formatResearchApiError(err);
        setPapers((prev) => {
          const m = new Map(prev);
          for (const wid of ids) {
            m.set(wid, {
              workId: wid,
              title: "",
              loading: false,
              error: msg,
            });
          }
          return m;
        });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [workIdsKey, effectiveWorkIds]);

  return { papers };
}
