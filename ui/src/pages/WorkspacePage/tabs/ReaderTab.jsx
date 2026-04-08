import React from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import ReaderWorkBody from "../../../components/work/ReaderWorkBody.jsx";
import { CursorSmallButton } from "../../../components/common/index.js";
import { buildWorkspaceTracePath, readTraceabilityState } from "../../../components/work/traceabilityState.js";

/**
 * @param {{ workId: string }} props
 */
export default function ReaderTab({ workId }) {
  const [searchParams] = useSearchParams();
  const trace = readTraceabilityState(searchParams);

  if (!workId.trim()) {
    return (
      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>
        Pick a work from Corpus to load the reader.
      </Typography>
    );
  }

  return (
    <Box>
      <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem", mb: 2 }}>
        Live: <code style={{ color: "rgba(129,140,248,0.95)" }}>GET /v1/works/{"{work_id}"}</code> +{" "}
        <code style={{ color: "rgba(129,140,248,0.95)" }}>/chunks</code>.
      </Typography>
      <Box sx={{ mb: 1.5, display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
        <CursorSmallButton component={Link} to={`/reader?work_id=${encodeURIComponent(workId)}`} sx={{ textDecoration: "none" }}>
          Open standalone Reader
        </CursorSmallButton>
        <CursorSmallButton
          component={Link}
          to={buildWorkspaceTracePath(workId, "graph", {
            section: trace.section,
            citation: trace.citation,
          })}
          sx={{ textDecoration: "none" }}
        >
          Jump to Graph
        </CursorSmallButton>
      </Box>
      <ReaderWorkBody
        workId={workId}
        focusedFingerprint={trace.chunkFingerprint}
        focusedSection={trace.section}
        citation={trace.citation}
      />
    </Box>
  );
}
