import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import ChatBubbleOutlineOutlinedIcon from "@mui/icons-material/ChatBubbleOutlineOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";

import { CursorIconAction } from "../../../components/common/index.js";
import { useWorkspaceContext } from "../../../components/layout/useWorkspaceContext.js";
import WorkIdGlossaryHint from "../../../components/layout/WorkIdGlossaryHint.jsx";
import GraphWorkspacePanel from "../../../components/graph/GraphWorkspacePanel.jsx";
import { GraphMissingWorkInline } from "../../../components/graph/graphShellStates.jsx";
import {
  buildStandaloneChatPath,
  buildStandaloneTracePath,
  buildWorkspaceTracePath,
  mergeTraceabilityStateWithHashSelection,
  readTraceabilityState,
  replaceHashTraceabilitySelection,
} from "../../../components/work/traceabilityState.js";
import { useHashTraceabilityGraphSelection } from "../../../components/work/useHashTraceabilityGraphSelection.js";
import { useI18n } from "../../../i18n/useI18n.js";

/**
 * @param {{ workId: string }} props
 */
export default function GraphTab({ workId }) {
  const { t } = useI18n();
  const { activeWorkspaceId } = useWorkspaceContext();
  const workspaceIdForGraph = String(activeWorkspaceId || "").trim();
  const [searchParams] = useSearchParams();
  const traceRouter = useMemo(() => readTraceabilityState(searchParams), [searchParams]);
  const hashSel = useHashTraceabilityGraphSelection();
  const trace = useMemo(() => mergeTraceabilityStateWithHashSelection(traceRouter, hashSel), [traceRouter, hashSel]);
  const graphTargetKey = String(workId || "").trim();
  const [selectedTrace, setSelectedTrace] = useState(() => ({
    targetKey: graphTargetKey,
    nodeId: trace.nodeId,
    edgeId: trace.edgeId,
  }));

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional URL↔state sync
    setSelectedTrace((prev) => {
      if (prev.targetKey !== graphTargetKey) {
        return { targetKey: graphTargetKey, nodeId: trace.nodeId, edgeId: trace.edgeId };
      }
      if (prev.nodeId === trace.nodeId && prev.edgeId === trace.edgeId) return prev;
      return { ...prev, nodeId: trace.nodeId, edgeId: trace.edgeId };
    });
  }, [graphTargetKey, trace.nodeId, trace.edgeId]);

  const selectedNodeId = selectedTrace.targetKey === graphTargetKey ? selectedTrace.nodeId : trace.nodeId;
  const selectedEdgeId = selectedTrace.targetKey === graphTargetKey ? selectedTrace.edgeId : trace.edgeId;
  const labMode = searchParams.get("lab") === "1";

  const handleReconcileSelection = useCallback(
    ({ nodeId, edgeId }) => {
      setSelectedTrace({ targetKey: graphTargetKey, nodeId, edgeId });
      replaceHashTraceabilitySelection({ nodeId, edgeId });
    },
    [graphTargetKey],
  );

  function handleSelectNode(nodeId) {
    const next = String(nodeId || "").trim();
    setSelectedTrace({ targetKey: graphTargetKey, nodeId: next, edgeId: "" });
    replaceHashTraceabilitySelection({ nodeId: next, edgeId: "" });
  }

  function handleSelectEdge(edgeId) {
    const next = String(edgeId || "").trim();
    setSelectedTrace({ targetKey: graphTargetKey, nodeId: "", edgeId: next });
    replaceHashTraceabilitySelection({ nodeId: "", edgeId: next });
  }

  if (!workId.trim()) {
    return <GraphMissingWorkInline message={t("wsTab.graph.pickWork")} />;
  }

  return (
    <Box>
      <Box sx={{ mb: 1.5, display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
        <CursorIconAction
          component={Link}
          to={buildStandaloneTracePath("/graph", workId, {
            nodeId: selectedNodeId,
            edgeId: selectedEdgeId,
            chunkFingerprint: trace.chunkFingerprint,
            section: trace.section,
            citation: trace.citation,
          })}
          title={t("wsTab.graph.openStandalone")}
        >
          <OpenInNewOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconAction>
        <CursorIconAction
          component={Link}
          to={buildWorkspaceTracePath(workId, "reader", {
            chunkFingerprint: trace.chunkFingerprint,
            section: trace.section,
            citation: trace.citation,
          })}
          title={t("wsTab.graph.jumpReader")}
        >
          <MenuBookOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconAction>
        <CursorIconAction
          component={Link}
          to={buildWorkspaceTracePath(workId, "evidence", {
            chunkFingerprint: trace.chunkFingerprint,
            section: trace.section,
            citation: trace.citation,
          })}
          title={t("wsTab.graph.jumpEvidence")}
        >
          <DescriptionOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconAction>
        <CursorIconAction
          component={Link}
          to={buildStandaloneChatPath(workId, {
            workspaceId: trace.workspaceId,
            nodeId: selectedNodeId,
            chunkFingerprint: trace.chunkFingerprint,
            section: trace.section,
            citation: trace.citation,
          })}
          title={t("wsTab.graph.jumpAsk")}
        >
          <ChatBubbleOutlineOutlinedIcon sx={{ fontSize: "1.05rem" }} />
        </CursorIconAction>
      </Box>

      <GraphWorkspacePanel
        workId={workId}
        workspaceId={workspaceIdForGraph}
        selectedNodeId={selectedNodeId}
        onSelectNode={handleSelectNode}
        selectedEdgeId={selectedEdgeId}
        onSelectEdge={handleSelectEdge}
        onReconcileSelection={handleReconcileSelection}
        mode="embedded"
        labMode={labMode}
        title={t("workspace.header.workspaceGraph")}
        subtitle={
          <Box>
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)" }}>{t("wsTab.graph.subtitle")}</Typography>
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.75 }}>
              <WorkIdGlossaryHint variant="graph" />
            </Typography>
          </Box>
        }
        traceContext={{
          chunkFingerprint: trace.chunkFingerprint,
          section: trace.section,
          citation: trace.citation,
        }}
      />
    </Box>
  );
}
