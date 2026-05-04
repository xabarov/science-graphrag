import React, { useCallback, useEffect, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";

import { CursorIconAction } from "../components/common/index.js";
import { useWorkspaceContext } from "../components/layout/useWorkspaceContext.js";
import GraphWorkspacePanel from "../components/graph/workspace/GraphWorkspacePanel.jsx";
import { GraphMissingWorkCallout } from "../components/graph/shell/graphShellStates.jsx";
import { persistWorkId } from "./WorkspacePage/utils/workContext.js";
import {
  GRAPH_PAGE_QUERY_KEYS,
  mergeTraceabilityParams,
  readGraphPageLayoutFlags,
  readTraceabilityState,
} from "../routing/index.js";
import { useI18n } from "../i18n/useI18n.js";

const GRAPH_SEARCH_MERGE_OPTS = { includeTab: false };

export default function GraphPage() {
  const { t } = useI18n();
  const { getLastWorkspaceHref, activeWorkspaceId } = useWorkspaceContext();
  const [searchParams, setSearchParams] = useSearchParams();
  const trace = useMemo(() => readTraceabilityState(searchParams), [searchParams]);
  const workId = trace.workId;
  const workspaceId = trace.workspaceId;
  const workspaceIdFromUrl = workspaceId.trim();
  const workIdTrimmed = workId.trim();
  // If URL names a work but omits workspace_id, do not fall back to the shell's active workspace
  // (see useGraphWorkspaceData / paper-card graph links).
  const effectiveWorkspaceId = workIdTrimmed
    ? workspaceIdFromUrl
    : workspaceIdFromUrl || String(activeWorkspaceId || "").trim();

  const labMode = searchParams.get(GRAPH_PAGE_QUERY_KEYS.lab) === "1";
  const { compact, focus, compactLayout } = readGraphPageLayoutFlags(searchParams);
  const chromeDense = compact || focus;

  useEffect(() => {
    if (workId.trim()) persistWorkId(workId);
  }, [workId]);

  const handleReconcileSelection = useCallback(({ nodeId, edgeId }) => {
    setSearchParams(
      (prev) => mergeTraceabilityParams(prev, { nodeId, edgeId }, GRAPH_SEARCH_MERGE_OPTS),
      { replace: true },
    );
  }, [setSearchParams]);

  const handleSelectNode = useCallback(
    (nodeId) => {
      const next = String(nodeId || "").trim();
      setSearchParams(
        (prev) => mergeTraceabilityParams(prev, { nodeId: next, edgeId: "" }, GRAPH_SEARCH_MERGE_OPTS),
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const handleSelectEdge = useCallback(
    (edgeId) => {
      const next = String(edgeId || "").trim();
      setSearchParams(
        (prev) => mergeTraceabilityParams(prev, { nodeId: "", edgeId: next }, GRAPH_SEARCH_MERGE_OPTS),
        { replace: true },
      );
    },
    [setSearchParams],
  );

  return (
    <Box
      sx={{
        flex: 1,
        minHeight: 0,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        px: chromeDense ? 0.75 : 1,
        pt: chromeDense ? 0.25 : 0.5,
        pb: chromeDense ? 0.25 : 0.5,
        width: "100%",
        maxWidth: "100%",
        boxSizing: "border-box",
      }}
    >
      {!workId.trim() && !effectiveWorkspaceId ? (
        <Box sx={{ flexShrink: 0, mb: 0.5 }}>
          <GraphMissingWorkCallout
            title={t("graph.missing.title")}
            description={t("graph.missing.description")}
            footnote={t("graph.missing.footnote")}
          />
          <Box sx={{ mt: 1.5 }}>
            <CursorIconAction component={Link} to={getLastWorkspaceHref()} title={t("graph.openLastWorkspace")}>
              <HubOutlinedIcon sx={{ fontSize: "1.15rem" }} />
            </CursorIconAction>
          </Box>
        </Box>
      ) : null}

      <Box sx={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <GraphWorkspacePanel
          workId={workId}
          workspaceId={effectiveWorkspaceId}
          selectedNodeId={trace.nodeId}
          onSelectNode={handleSelectNode}
          selectedEdgeId={trace.edgeId}
          onSelectEdge={handleSelectEdge}
          onReconcileSelection={handleReconcileSelection}
          mode="standalone"
          compactLayout={compactLayout}
          focusLayout={focus}
          labMode={labMode}
          title=""
          subtitle={null}
          traceContext={{
            chunkFingerprint: trace.chunkFingerprint,
            section: trace.section,
            citation: trace.citation,
          }}
        />
      </Box>
    </Box>
  );
}
