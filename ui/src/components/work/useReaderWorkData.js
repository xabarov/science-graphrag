import { useEffect, useMemo, useState } from "react";

import { formatResearchApiError, getWorkChunks, getWorkDetail, getWorkSources } from "../../services/researchApi.js";

/**
 * Load work detail, chunks, and sources for Reader body.
 * @param {string} workId
 */
export function useReaderWorkData(workId) {
  const [detail, setDetail] = useState(null);
  const [chunks, setChunks] = useState(null);
  const [sourcesPayload, setSourcesPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState("markdown");

  useEffect(() => {
    if (!workId.trim()) {
      setDetail(null);
      setChunks(null);
      setError(null);
      setSourcesPayload(null);
      setViewMode("markdown");
      return undefined;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      setViewMode("markdown");
      try {
        const [dRes, cRes, sRes] = await Promise.all([
          getWorkDetail(workId),
          getWorkChunks(workId, { limit: 200, offset: 0 }),
          getWorkSources(workId).catch(() => ({ data: null })),
        ]);
        if (cancelled) return;
        setDetail(dRes.data);
        setChunks(cRes.data);
        setSourcesPayload(sRes.data);
      } catch (err) {
        if (cancelled) return;
        setError(formatResearchApiError(err));
        setDetail(null);
        setChunks(null);
        setSourcesPayload(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workId]);

  const pdfAvailable = useMemo(() => {
    const rows = sourcesPayload?.sources;
    if (!Array.isArray(rows)) return false;
    const pdf = rows.find((s) => s && String(s.repr || "").toLowerCase() === "pdf");
    return Boolean(pdf?.available);
  }, [sourcesPayload]);

  useEffect(() => {
    if (!pdfAvailable && viewMode === "pdf") setViewMode("markdown");
  }, [pdfAvailable, viewMode]);

  return {
    detail,
    chunks,
    sourcesPayload,
    loading,
    error,
    pdfAvailable,
    viewMode,
    setViewMode,
  };
}
