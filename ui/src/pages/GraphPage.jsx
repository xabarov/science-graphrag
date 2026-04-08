import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";

import { CursorPrimaryButton, CursorSmallButton } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import GraphWorkspacePanel from "../components/graph/GraphWorkspacePanel.jsx";
import { persistWorkId } from "./WorkspacePage/utils/workContext.js";
import { buildWorkspaceTracePath, mergeTraceabilityParams, readTraceabilityState } from "../components/work/traceabilityState.js";

export default function GraphPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initial = searchParams.get("work_id") || "";
  const [workIdInput, setWorkIdInput] = useState(initial);
  const trace = readTraceabilityState(searchParams);
  const workId = trace.workId;
  const selectedNodeId = trace.nodeId;

  useEffect(() => {
    setWorkIdInput(workId);
  }, [workId]);

  useEffect(() => {
    if (workId.trim()) persistWorkId(workId);
  }, [workId]);

  function applyWorkId(e) {
    e.preventDefault();
    const next = workIdInput.trim();
    if (next) {
      persistWorkId(next);
      setSearchParams({ work_id: next });
    } else setSearchParams({});
  }

  function handleSelectNode(nodeId) {
    const params = mergeTraceabilityParams(searchParams, { nodeId });
    setSearchParams(params, { replace: false });
  }

  return (
    <Box sx={{ p: 2, maxWidth: 1200 }}>
      <PageHeader
        eyebrow="Direct tool"
        title="Graph"
        description="Use the standalone graph surface for node-focused inspection while keeping the same data model that powers Workspace Graph."
        actions={
          <>
            <CursorSmallButton component={Link} to="/workspace" sx={{ textDecoration: "none" }}>
              Workspace
            </CursorSmallButton>
            <CursorSmallButton component={Link} to="/corpus" sx={{ textDecoration: "none" }}>
              Corpus
            </CursorSmallButton>
          </>
        }
      />

      <Box component="form" onSubmit={applyWorkId} sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
        <TextField
          label="work_id"
          value={workIdInput}
          onChange={(ev) => setWorkIdInput(ev.target.value)}
          size="small"
          fullWidth
          sx={{
            maxWidth: 480,
            "& .MuiInputBase-input": { fontSize: "0.8125rem" },
            "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
          }}
        />
        <CursorPrimaryButton type="submit">Load</CursorPrimaryButton>
      </Box>

      {!workId.trim() ? (
        <Box
          sx={{
            mb: 2,
            p: 2,
            borderRadius: "6px",
            border: "1px dashed rgba(255,255,255,0.12)",
            backgroundColor: "rgba(255,255,255,0.02)",
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)" }}>No graph context yet</Typography>
          <Typography sx={{ mt: 0.75, fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}>
            Load a `work_id` to inspect graph nodes directly, or open a paper in Workspace and jump here when you need a dedicated graph surface.
          </Typography>
          <Typography sx={{ mt: 1, fontSize: "0.75rem", color: "rgba(255,255,255,0.42)" }}>
            Phase 4 (master plan): richer canvas, controls, and a dedicated graph-first detail panel are the next UX layer on top of this surface.
          </Typography>
        </Box>
      ) : null}

      {workId.trim() ? (
        <Box sx={{ mb: 1.5, display: "flex", flexWrap: "wrap", gap: 1 }}>
          <CursorSmallButton
            component={Link}
            to={buildWorkspaceTracePath(workId, "graph", {
              nodeId: selectedNodeId,
              chunkFingerprint: trace.chunkFingerprint,
              section: trace.section,
              citation: trace.citation,
            })}
            sx={{ textDecoration: "none" }}
          >
            Open Graph in workspace
          </CursorSmallButton>
          <CursorSmallButton
            component={Link}
            to={buildWorkspaceTracePath(workId, "reader", {
              nodeId: selectedNodeId,
              chunkFingerprint: trace.chunkFingerprint,
              section: trace.section,
              citation: trace.citation,
            })}
            sx={{ textDecoration: "none" }}
          >
            Open Reader in workspace
          </CursorSmallButton>
          <CursorSmallButton
            component={Link}
            to={buildWorkspaceTracePath(workId, "evidence", {
              nodeId: selectedNodeId,
              chunkFingerprint: trace.chunkFingerprint,
              section: trace.section,
              citation: trace.citation,
            })}
            sx={{ textDecoration: "none" }}
          >
            Open Evidence in workspace
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
            Open Ask in workspace
          </CursorSmallButton>
        </Box>
      ) : null}

      <GraphWorkspacePanel
        workId={workId}
        selectedNodeId={selectedNodeId}
        onSelectNode={handleSelectNode}
        mode="standalone"
        title="Graph lab"
        subtitle="Use this standalone view for node-focused inspection, while Workspace Graph keeps the same context embedded in the main research flow."
        traceContext={{
          chunkFingerprint: trace.chunkFingerprint,
          section: trace.section,
          citation: trace.citation,
        }}
      />
    </Box>
  );
}
