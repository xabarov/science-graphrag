import React, { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import Chip from "@mui/material/Chip";
import { Link } from "react-router-dom";

import { getWorkChunks } from "../../services/researchApi.js";
import { CursorSmallButton } from "../common/index.js";
import { buildWorkspaceTracePath, describeTraceabilityState } from "./traceabilityState.js";

/**
 * Evidence (chunk fingerprints) for a fixed work_id.
 * @param {{ workId: string, highlightedFingerprint?: string, highlightedSection?: string, citation?: string }} props
 */
export default function EvidenceWorkBody({
  workId,
  highlightedFingerprint = "",
  highlightedSection = "",
  citation = "",
}) {
  const [chunks, setChunks] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const traceSummary = describeTraceabilityState({
    chunkFingerprint: highlightedFingerprint,
    section: highlightedSection,
    citation,
  });

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
          {traceSummary.length > 0 ? (
            <Box
              sx={{
                p: 1.25,
                borderRadius: "6px",
                border: "1px solid rgba(99,102,241,0.2)",
                backgroundColor: "rgba(99,102,241,0.08)",
              }}
            >
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)", mb: 0.5 }}>Opened from traceability flow</Typography>
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.8)" }}>
                Focus: {traceSummary.join(" · ")}
              </Typography>
            </Box>
          ) : null}
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>total: {chunks.total ?? "—"}</Typography>
          {(chunks.items || []).map((ch) => (
            (() => {
              const fingerprint = String(ch.chunk_fingerprint || "");
              const sectionPath = String(ch.section_path || "");
              const highlighted =
                (highlightedFingerprint && fingerprint === highlightedFingerprint) ||
                (highlightedSection && sectionPath === highlightedSection);
              return (
            <Box
              key={`${ch.chunk_fingerprint}-${ch.order}`}
              sx={{
                py: 0.9,
                px: 0.75,
                borderRadius: "6px",
                border: highlighted ? "1px solid rgba(99,102,241,0.32)" : "1px solid transparent",
                backgroundColor: highlighted ? "rgba(99,102,241,0.08)" : "transparent",
                borderBottom: highlighted ? "1px solid rgba(99,102,241,0.32)" : "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.75 }}>
                <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.9)", fontFamily: "monospace" }}>
                  {ch.chunk_fingerprint}
                </Typography>
                {highlighted ? <Chip label="answer-linked" size="small" sx={{ height: 20, fontSize: "0.6875rem" }} /> : null}
              </Box>
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.25 }}>{ch.section_path || "—"}</Typography>
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)", mt: 0.35 }}>
                {(ch.text || "").slice(0, 600)}
                {(ch.text || "").length > 600 ? "…" : ""}
              </Typography>
              <Box sx={{ mt: 0.75, display: "flex", flexWrap: "wrap", gap: 1 }}>
                <CursorSmallButton
                  component={Link}
                  to={buildWorkspaceTracePath(workId, "reader", {
                    chunkFingerprint: fingerprint,
                    section: sectionPath,
                    citation,
                  })}
                  sx={{ textDecoration: "none" }}
                >
                  Open in Reader
                </CursorSmallButton>
                <CursorSmallButton
                  component={Link}
                  to={buildWorkspaceTracePath(workId, "graph", {
                    section: sectionPath,
                    citation,
                  })}
                  sx={{ textDecoration: "none" }}
                >
                  Open in Graph
                </CursorSmallButton>
              </Box>
            </Box>
              );
            })()
          ))}
        </Box>
      )}
    </Box>
  );
}
