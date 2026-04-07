import React, { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";

import { getWorkChunks, getWorkDetail } from "../../services/researchApi.js";

/**
 * Reader content for a fixed work_id (used by Reader tab and standalone Reader page).
 * @param {{ workId: string }} props
 */
export default function ReaderWorkBody({ workId }) {
  const [detail, setDetail] = useState(null);
  const [chunks, setChunks] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!workId.trim()) {
      setDetail(null);
      setChunks(null);
      setError(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [dRes, cRes] = await Promise.all([
          getWorkDetail(workId),
          getWorkChunks(workId, { limit: 80, offset: 0 }),
        ]);
        if (cancelled) return;
        setDetail(dRes.data);
        setChunks(cRes.data);
      } catch (err) {
        if (cancelled) return;
        const msg = err?.response?.data?.detail
          ? JSON.stringify(err.response.data.detail)
          : err?.message || String(err);
        setError(msg);
        setDetail(null);
        setChunks(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workId]);

  return (
    <Box>
      {loading && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
          <CircularProgress size={22} sx={{ color: "rgba(129,140,248,0.9)" }} />
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>Loading…</Typography>
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {error}
        </Alert>
      )}

      {detail && !loading && (
        <Box sx={{ mb: 2, p: 1.5, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a" }}>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{detail.title || "(no title)"}</Typography>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mt: 0.5 }}>
            {detail.year != null ? `${detail.year} · ` : ""}
            {detail.doi ? `DOI ${detail.doi} · ` : ""}
            {detail.arxiv_id ? `arXiv ${detail.arxiv_id}` : ""}
          </Typography>
          {detail.abstract && (
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)", mt: 1, whiteSpace: "pre-wrap" }}>
              {detail.abstract}
            </Typography>
          )}
          {detail.ingestion && (
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 1 }}>
              document_id: {detail.ingestion.document_id} · has_chunks: {String(detail.ingestion.has_chunks)} · semantic:{" "}
              {String(detail.ingestion.has_semantic_layer)}
            </Typography>
          )}
        </Box>
      )}

      {chunks && !loading && (
        <>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 1 }}>
            Chunks ({chunks.total ?? (chunks.items || []).length})
          </Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
            {(chunks.items || []).map((ch) => (
              <Box
                key={`${ch.chunk_fingerprint}-${ch.order}`}
                sx={{
                  p: 1.5,
                  borderRadius: "6px",
                  border: "1px solid rgba(255,255,255,0.08)",
                  backgroundColor: "#141414",
                }}
              >
                <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>
                  {ch.section_path || "—"} · fp {ch.chunk_fingerprint}
                </Typography>
                <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", mt: 0.5, whiteSpace: "pre-wrap" }}>
                  {(ch.text || "").slice(0, 4000)}
                  {(ch.text || "").length > 4000 ? "…" : ""}
                </Typography>
              </Box>
            ))}
          </Box>
        </>
      )}
    </Box>
  );
}
