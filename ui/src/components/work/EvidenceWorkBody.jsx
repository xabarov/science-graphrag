import React, { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";

import { getWorkChunks } from "../../services/researchApi.js";

/**
 * Evidence (chunk fingerprints) for a fixed work_id.
 * @param {{ workId: string }} props
 */
export default function EvidenceWorkBody({ workId }) {
  const [chunks, setChunks] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!workId.trim()) {
      setChunks(null);
      setError(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getWorkChunks(workId, { limit: 200, offset: 0 });
        if (cancelled) return;
        setChunks(res.data);
      } catch (err) {
        if (cancelled) return;
        const msg = err?.response?.data?.detail
          ? JSON.stringify(err.response.data.detail)
          : err?.message || String(err);
        setError(msg);
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
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>Loading chunks…</Typography>
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {error}
        </Alert>
      )}

      {chunks && !loading && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>total: {chunks.total ?? "—"}</Typography>
          {(chunks.items || []).map((ch) => (
            <Box
              key={`${ch.chunk_fingerprint}-${ch.order}`}
              sx={{
                py: 0.75,
                borderBottom: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.9)", fontFamily: "monospace" }}>
                {ch.chunk_fingerprint}
              </Typography>
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>{ch.section_path || "—"}</Typography>
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)", mt: 0.25 }}>
                {(ch.text || "").slice(0, 600)}
                {(ch.text || "").length > 600 ? "…" : ""}
              </Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}
