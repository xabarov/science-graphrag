import React from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../../../components/common/index.js";
import GraphWorkspacePanel from "../../../components/graph/GraphWorkspacePanel.jsx";
import { buildStandaloneTracePath, buildWorkspaceTracePath, mergeTraceabilityParams, readTraceabilityState } from "../../../components/work/traceabilityState.js";

/**
 * @param {{ workId: string }} props
 */
export default function GraphTab({ workId }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const trace = readTraceabilityState(searchParams);
  const selectedNodeId = trace.nodeId;

  if (!workId.trim()) {
    return (
      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>
        Pick a work from Corpus to inspect graph context.
      </Typography>
    );
  }

  function handleSelectNode(nodeId) {
    const params = mergeTraceabilityParams(searchParams, { nodeId });
    setSearchParams(params, { replace: false });
  }

  return (
    <Box>
      <Box sx={{ mb: 1.5, display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
        <CursorSmallButton
          component={Link}
          to={buildStandaloneTracePath("/graph", workId, {
            nodeId: selectedNodeId,
            chunkFingerprint: trace.chunkFingerprint,
            section: trace.section,
            citation: trace.citation,
          })}
          sx={{ textDecoration: "none" }}
        >
          Open standalone Graph
        </CursorSmallButton>
        <CursorSmallButton
          component={Link}
          to={buildWorkspaceTracePath(workId, "reader", {
            chunkFingerprint: trace.chunkFingerprint,
            section: trace.section,
            citation: trace.citation,
          })}
          sx={{ textDecoration: "none" }}
        >
          Jump to Reader
        </CursorSmallButton>
        <CursorSmallButton
          component={Link}
          to={buildWorkspaceTracePath(workId, "evidence", {
            chunkFingerprint: trace.chunkFingerprint,
            section: trace.section,
            citation: trace.citation,
          })}
          sx={{ textDecoration: "none" }}
        >
          Jump to Evidence
        </CursorSmallButton>
        <CursorSmallButton
          component={Link}
          to={buildWorkspaceTracePath(workId, "ask", {
            nodeId: selectedNodeId,
            chunkFingerprint: trace.chunkFingerprint,
            section: trace.section,
            citation: trace.citation,
          })}
          sx={{ textDecoration: "none" }}
        >
          Jump to Ask
        </CursorSmallButton>
      </Box>

      <GraphWorkspacePanel
        workId={workId}
        selectedNodeId={selectedNodeId}
        onSelectNode={handleSelectNode}
        mode="embedded"
        title="Workspace graph"
        subtitle="Graph stays tied to the active work and keeps URL-driven node focus for deep links."
        traceContext={{
          chunkFingerprint: trace.chunkFingerprint,
          section: trace.section,
          citation: trace.citation,
        }}
      />
    </Box>
  );
}
