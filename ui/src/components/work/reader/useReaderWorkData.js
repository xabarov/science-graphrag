import { useEffect, useMemo, useState } from "react";

import {
  formatResearchApiError,
  getWorkChunks,
  getWorkDetail,
  getWorkExtractedBody,
  getWorkSources,
} from "../../services/researchApi.js";

/**
 * Load work detail, chunks, and sources for Reader body.
 * @param {string} workId
 */
export function useReaderWorkData(workId) {
  const [detail, setDetail] = useState(null);
  const [chunks, setChunks] = useState(null);
  const [sourcesPayload, setSourcesPayload] = useState(null);
  const [extractedBodyPayload, setExtractedBodyPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState("ocr");

  useEffect(() => {
    if (!workId.trim()) {
      setDetail(null);
      setChunks(null);
      setError(null);
      setSourcesPayload(null);
      setExtractedBodyPayload(null);
      setViewMode("ocr");
      return undefined;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      setViewMode("ocr");
      try {
        const [dRes, cRes, sRes, eRes] = await Promise.all([
          getWorkDetail(workId),
          getWorkChunks(workId, { limit: 200, offset: 0 }),
          getWorkSources(workId).catch(() => ({ data: null })),
          getWorkExtractedBody(workId).catch(() => ({ data: null })),
        ]);
        if (cancelled) return;
        setDetail(dRes.data);
        setChunks(cRes.data);
        setSourcesPayload(sRes.data);
        setExtractedBodyPayload(eRes.data);
      } catch (err) {
        if (cancelled) return;
        setError(formatResearchApiError(err));
        setDetail(null);
        setChunks(null);
        setSourcesPayload(null);
        setExtractedBodyPayload(null);
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
    if (!pdfAvailable && viewMode === "pdf") setViewMode("ocr");
  }, [pdfAvailable, viewMode]);

  /** Prefer PDF when there are no text chunks but an original PDF exists (avoids an empty main column). */
  useEffect(() => {
    if (loading || !chunks || !pdfAvailable) return;
    const totalField = Number(chunks.total);
    const items = Array.isArray(chunks.items) ? chunks.items : [];
    const effectiveTotal = Number.isFinite(totalField) && totalField > 0 ? totalField : items.length;
    const hasExtracted = Boolean(detail?.ingestion?.has_extracted_body);
    if (effectiveTotal === 0 && !hasExtracted) setViewMode("pdf");
  }, [loading, chunks, pdfAvailable, detail?.ingestion?.has_extracted_body]);


  return {
    detail,
    chunks,
    sourcesPayload,
    extractedBodyPayload,
    loading,
    error,
    pdfAvailable,
    viewMode,
    setViewMode,
  };
}
