import React from "react";
import { useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import AskPanel from "../../../components/work/AskPanel.jsx";
import { readTraceabilityState } from "../../../components/work/traceabilityState.js";

/**
 * @param {{ workId: string }} props
 */
export default function AskTab({ workId }) {
  const [searchParams] = useSearchParams();
  const trace = readTraceabilityState(searchParams);

  if (!workId.trim()) {
    return (
      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>
        Pick a work from Corpus to scope questions to that work.
      </Typography>
    );
  }

  return (
    <Box>
      {(trace.nodeId || trace.chunkFingerprint || trace.section || trace.citation) ? (
        <Box
          sx={{
            mb: 2,
            p: 1.25,
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.08)",
            backgroundColor: "#1a1a1a",
          }}
        >
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Research context</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.8)", mt: 0.5 }}>
            {trace.citation ? `Citation #${trace.citation} · ` : ""}
            {trace.chunkFingerprint ? `chunk ${trace.chunkFingerprint} · ` : ""}
            {trace.section ? `section ${trace.section} · ` : ""}
            {trace.nodeId ? `node ${trace.nodeId}` : ""}
          </Typography>
        </Box>
      ) : null}
      <AskPanel scopedWorkId={workId} showPageChrome={false} workspaceWorkId={workId} />
    </Box>
  );
}
