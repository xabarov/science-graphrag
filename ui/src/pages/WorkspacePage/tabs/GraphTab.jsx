import React from "react";
import { Link, useSearchParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { CursorSmallButton } from "../../../components/common/index.js";
import WorkIdGlossaryHint from "../../../components/layout/WorkIdGlossaryHint.jsx";
import GraphWorkspacePanel from "../../../components/graph/GraphWorkspacePanel.jsx";
import { GraphMissingWorkInline } from "../../../components/graph/graphShellStates.jsx";
import {
  buildStandaloneTracePath,
  buildWorkspaceTracePath,
  mergeTraceabilityParams,
  readTraceabilityState,
} from "../../../components/work/traceabilityState.js";
import { useI18n } from "../../../i18n/I18nContext.jsx";

/**
 * @param {{ workId: string }} props
 */
export default function GraphTab({ workId }) {
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const trace = readTraceabilityState(searchParams);
  const selectedNodeId = trace.nodeId;
  const selectedEdgeId = trace.edgeId;
  const labMode = searchParams.get("lab") === "1";

  if (!workId.trim()) {
    return <GraphMissingWorkInline message={t("wsTab.graph.pickWork")} />;
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
    <Box>
      <Box sx={{ mb: 1.5, display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
        <CursorSmallButton
          component={Link}
          to={buildStandaloneTracePath("/graph", workId, {
            nodeId: selectedNodeId,
            edgeId: selectedEdgeId,
            chunkFingerprint: trace.chunkFingerprint,
            section: trace.section,
            citation: trace.citation,
          })}
          sx={{ textDecoration: "none" }}
        >
          {t("wsTab.graph.openStandalone")}
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
          {t("wsTab.graph.jumpReader")}
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
          {t("wsTab.graph.jumpEvidence")}
        </CursorSmallButton>
        <CursorSmallButton
          component={Link}
          to={`/workspace?${mergeTraceabilityParams(searchParams, {
            workId,
            tab: "ask",
            nodeId: selectedNodeId,
            chunkFingerprint: trace.chunkFingerprint,
            section: trace.section,
            citation: trace.citation,
          }).toString()}`}
          sx={{ textDecoration: "none" }}
        >
          {t("wsTab.graph.jumpAsk")}
        </CursorSmallButton>
      </Box>

      <GraphWorkspacePanel
        workId={workId}
        selectedNodeId={selectedNodeId}
        onSelectNode={handleSelectNode}
        selectedEdgeId={selectedEdgeId}
        onSelectEdge={handleSelectEdge}
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
          edgeId: selectedEdgeId,
        }}
      />
    </Box>
  );
}
