import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";

import { CursorSmallButton } from "../../../components/common/index.js";
import { formatResearchApiError, getWorkDetail } from "../../../services/researchApi.js";
import { buildWorkspacePath } from "../utils/workContext.js";

/**
 * @param {{ workId: string }} props
 */
export default function OverviewTab({ workId }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!workId.trim()) {
      setDetail(null);
      setError(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getWorkDetail(workId);
        if (cancelled) return;
        setDetail(res.data);
      } catch (err) {
        if (cancelled) return;
        setError(formatResearchApiError(err));
        setDetail(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workId]);

  if (!workId.trim()) {
    return (
      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>
        Select a work from Corpus to see an overview.
      </Typography>
    );
  }

  return (
    <Box>
      {loading && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
          <CircularProgress size={22} sx={{ color: "rgba(129,140,248,0.9)" }} />
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>Loading work…</Typography>
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {error}
        </Alert>
      )}

      {detail && !loading && (
        <>
          <Box sx={{ p: 1.5, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a", mb: 2 }}>
            <Typography sx={{ fontWeight: 600, fontSize: "0.9375rem" }}>{detail.title || "(no title)"}</Typography>
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mt: 0.5 }}>
              {detail.year != null ? `${detail.year} · ` : ""}
              {detail.doi ? `DOI ${detail.doi} · ` : ""}
              {detail.arxiv_id ? `arXiv ${detail.arxiv_id}` : ""}
            </Typography>
            {detail.abstract ? (
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)", mt: 1.5, whiteSpace: "pre-wrap" }}>
                {detail.abstract}
              </Typography>
            ) : null}
            {detail.ingestion ? (
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 1 }}>
                document_id: {detail.ingestion.document_id} · has_chunks: {String(detail.ingestion.has_chunks)} · semantic:{" "}
                {String(detail.ingestion.has_semantic_layer)}
              </Typography>
            ) : null}
          </Box>

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 1 }}>Quick actions</Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
            <CursorSmallButton component={Link} to={buildWorkspacePath(workId, "reader")} sx={{ textDecoration: "none" }}>
              Reader tab
            </CursorSmallButton>
            <CursorSmallButton component={Link} to={buildWorkspacePath(workId, "graph")} sx={{ textDecoration: "none" }}>
              Graph tab
            </CursorSmallButton>
            <CursorSmallButton component={Link} to={buildWorkspacePath(workId, "ask")} sx={{ textDecoration: "none" }}>
              Ask tab
            </CursorSmallButton>
            <CursorSmallButton component={Link} to={buildWorkspacePath(workId, "evidence")} sx={{ textDecoration: "none" }}>
              Evidence tab
            </CursorSmallButton>
            <CursorSmallButton component={Link} to={`/graph?work_id=${encodeURIComponent(workId)}`} sx={{ textDecoration: "none" }}>
              Open graph (full page)
            </CursorSmallButton>
          </Box>

          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 2 }}>
            Graph is now available inside workspace and still kept as a standalone route for deeper inspection.
          </Typography>
        </>
      )}
    </Box>
  );
}
