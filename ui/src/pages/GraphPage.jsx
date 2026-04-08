import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import TextField from "@mui/material/TextField";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { CursorPrimaryButton, CursorSmallButton } from "../components/common/index.js";
import PageHeader from "../components/layout/PageHeader.jsx";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";
import GraphWorkspacePanel from "../components/graph/GraphWorkspacePanel.jsx";
import { GraphMissingWorkCallout } from "../components/graph/graphShellStates.jsx";
import { persistWorkId } from "./WorkspacePage/utils/workContext.js";
import { buildWorkspaceTracePath, mergeTraceabilityParams, readTraceabilityState } from "../components/work/traceabilityState.js";
import { readGraphPageLayoutFlags, preserveGraphPageOptionalParams } from "./graphPageUrl.js";

const LS_GRAPH_PAGE_CHROME = "graphPageChromeExpanded";

export default function GraphPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initial = searchParams.get("work_id") || "";
  const [workIdInput, setWorkIdInput] = useState(initial);
  const trace = readTraceabilityState(searchParams);
  const workId = trace.workId;
  const selectedNodeId = trace.nodeId;
  const selectedEdgeId = trace.edgeId;
  const labMode = searchParams.get("lab") === "1";
  const { compact, focus, compactLayout } = readGraphPageLayoutFlags(searchParams);
  const chromeDense = compact || focus;

  const [chromeExpanded, setChromeExpanded] = useState(() => {
    if (typeof window === "undefined") return !chromeDense;
    if (chromeDense) return false;
    return window.localStorage.getItem(LS_GRAPH_PAGE_CHROME) !== "0";
  });
  const [linksExpanded, setLinksExpanded] = useState(() => !chromeDense);

  useEffect(() => {
    setWorkIdInput(workId);
  }, [workId]);

  useEffect(() => {
    if (workId.trim()) persistWorkId(workId);
  }, [workId]);

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_PAGE_CHROME, chromeExpanded ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [chromeExpanded]);

  function applyWorkId(e) {
    e.preventDefault();
    const next = workIdInput.trim();
    if (next) {
      persistWorkId(next);
      const params = new URLSearchParams();
      params.set("work_id", next);
      preserveGraphPageOptionalParams(params, searchParams);
      setSearchParams(params);
    } else {
      const cleared = new URLSearchParams();
      preserveGraphPageOptionalParams(cleared, searchParams);
      setSearchParams(cleared);
    }
  }

  function handleSelectNode(nodeId) {
    const params = mergeTraceabilityParams(searchParams, { nodeId, edgeId: "" });
    setSearchParams(params, { replace: false });
  }

  function handleSelectEdge(edgeId) {
    const params = mergeTraceabilityParams(searchParams, { edgeId, nodeId: "" });
    setSearchParams(params, { replace: false });
  }

  return (
    <Box
      sx={{
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        p: 2,
        ...mainShellContentSx,
        boxSizing: "border-box",
      }}
    >
      <Box sx={{ flexShrink: 0, display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
        <CursorSmallButton
          type="button"
          onClick={() => setChromeExpanded((v) => !v)}
          aria-expanded={chromeExpanded}
          aria-controls="graph-page-chrome"
          sx={{ minWidth: 36, px: 0.75 }}
        >
          <ExpandMoreIcon
            sx={{
              fontSize: "1.15rem",
              color: "rgba(255,255,255,0.65)",
              transform: chromeExpanded ? "rotate(0deg)" : "rotate(-90deg)",
              transition: "transform 0.15s ease",
            }}
          />
        </CursorSmallButton>
        <Box component="span" sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>
          Page info &amp; load
        </Box>
      </Box>

      <Collapse in={chromeExpanded}>
        <Box id="graph-page-chrome" sx={{ flexShrink: 0 }}>
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

          <Box
            component="form"
            onSubmit={applyWorkId}
            sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "flex-end", mb: 2 }}
          >
            <TextField
              label="work_id"
              value={workIdInput}
              onChange={(ev) => setWorkIdInput(ev.target.value)}
              size="small"
              sx={{
                flex: "1 1 200px",
                minWidth: 160,
                maxWidth: 520,
                "& .MuiInputBase-input": { fontSize: "0.8125rem" },
                "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
              }}
            />
            <CursorPrimaryButton type="submit">Load</CursorPrimaryButton>
          </Box>
        </Box>
      </Collapse>

      {!chromeExpanded ? (
        <Box
          component="form"
          onSubmit={applyWorkId}
          sx={{ flexShrink: 0, display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center", mb: 1 }}
        >
          <TextField
            label="work_id"
            value={workIdInput}
            onChange={(ev) => setWorkIdInput(ev.target.value)}
            size="small"
            sx={{
              flex: "1 1 180px",
              minWidth: 140,
              maxWidth: 400,
              "& .MuiInputBase-input": { fontSize: "0.8125rem" },
              "& .MuiInputLabel-root": { fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)" },
            }}
          />
          <CursorPrimaryButton type="submit">Load</CursorPrimaryButton>
          <CursorSmallButton component={Link} to="/workspace" sx={{ textDecoration: "none" }}>
            Workspace
          </CursorSmallButton>
        </Box>
      ) : null}

      {!workId.trim() ? (
        <GraphMissingWorkCallout
          title="No graph context yet"
          description="Load a work_id to inspect graph nodes directly, or open a paper in Workspace and jump here when you need a dedicated graph surface."
          footnote="Tip: append ?lab=1 to expand diagnostics by default (Graph Lab). Add ?compact=1 for a denser layout, or ?focus=1 to maximize canvas (Graph mode, secondary panels collapsed)."
        />
      ) : null}

      {workId.trim() ? (
        <Box sx={{ flexShrink: 0, mb: 1 }}>
          <CursorSmallButton
            type="button"
            onClick={() => setLinksExpanded((v) => !v)}
            aria-expanded={linksExpanded}
            sx={{ mb: linksExpanded ? 1 : 0 }}
          >
            {linksExpanded ? "Hide" : "Show"} workspace links
          </CursorSmallButton>
          <Collapse in={linksExpanded}>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
              <CursorSmallButton
                component={Link}
                to={buildWorkspaceTracePath(workId, "graph", {
                  nodeId: selectedNodeId,
                  edgeId: selectedEdgeId,
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
                  edgeId: selectedEdgeId,
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
                  edgeId: selectedEdgeId,
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
                  edgeId: selectedEdgeId,
                  chunkFingerprint: trace.chunkFingerprint,
                  section: trace.section,
                  citation: trace.citation,
                })}
                sx={{ textDecoration: "none" }}
              >
                Open Ask in workspace
              </CursorSmallButton>
            </Box>
          </Collapse>
        </Box>
      ) : null}

      <Box sx={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
        <GraphWorkspacePanel
          workId={workId}
          selectedNodeId={selectedNodeId}
          onSelectNode={handleSelectNode}
          selectedEdgeId={selectedEdgeId}
          onSelectEdge={handleSelectEdge}
          mode="standalone"
          compactLayout={compactLayout}
          focusLayout={focus}
          labMode={labMode}
          title="Graph lab"
          subtitle="Use this standalone view for node-focused inspection, while Workspace Graph keeps the same context embedded in the main research flow."
          traceContext={{
            chunkFingerprint: trace.chunkFingerprint,
            section: trace.section,
            citation: trace.citation,
            edgeId: selectedEdgeId,
          }}
        />
      </Box>
    </Box>
  );
}
