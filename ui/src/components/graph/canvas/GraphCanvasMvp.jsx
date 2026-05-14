import React from "react";
import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";

import GraphCanvasDenseLabelHint from "./GraphCanvasDenseLabelHint.jsx";
import GraphCanvasEmptyState from "./GraphCanvasEmptyState.jsx";
import GraphCanvasEdgeTypeLegend from "./GraphCanvasEdgeTypeLegend.jsx";
import GraphCanvasNodeContextMenu from "./GraphCanvasNodeContextMenu.jsx";
import GraphCanvasViewportControls from "./GraphCanvasViewportControls.jsx";
import GraphCanvasViewToolbar from "./GraphCanvasViewToolbar.jsx";
import { MIN_CANVAS_HEIGHT } from "./graphCanvasMvpConstants.js";
import { useI18n } from "../../../i18n/useI18n.js";
import { localizeEdgeType } from "../model/graphLocalize.js";
import { useGraphCanvasMvpController } from "./hooks/useGraphCanvasMvpController.js";

const EMPTY_COMMUNITY_MAP = new Map();

/*
 * Force-layout interaction contract (canvas MVP):
 * - In "force" mode, hit-testing reads live positions from simNodesRef via getPositionsForFrame() (Phase B: ref buffer).
 *   If the physics integrator mutates those positions between pointerdown and pointerup, the released click can miss
 *   the intended node; integration is therefore paused for primary pointer sessions on the canvas (see useGraphPhysicsPolicy).
 * - Shell drawer navigation dispatches a short navigation-intent pause so the router can commit before rAF-heavy work resumes.
 * - Add new integration pause reasons only in useGraphPhysicsPolicy (see hook JSDoc), not ad hoc rAF toggles here.
 *
 * Orchestration lives in hooks/useGraphCanvasMvpController.js (seam map in that file).
 */

export default function GraphCanvasMvp({
  graph,
  selectedNodeId,
  selectedEdgeId = "",
  onSelectNode,
  onSelectEdge,
  layoutMode = "circle",
  onCanvasLayoutModeChange,
  onAggregatorExpand,
  /** When non-empty and query is active, nodes not in this Set are drawn dimmed (local find). */
  searchMatchIds = null,
  /** Non-empty trimmed string enables search dimming on canvas. */
  searchQuery = "",
  /** Increment to center viewport on this node id without requiring prior selection. */
  centerRequestNonce = 0,
  centerRequestNodeId = "",
  graphColorBy = "type",
  onGraphColorByChange,
  graphCommunityHulls = false,
  onGraphCommunityHullsChange,
  nodeCommunityMap = EMPTY_COMMUNITY_MAP,
}) {
  const { t } = useI18n();
  const theme = useTheme();
  const tk = theme.appTokens;
  const appearance = theme.palette.mode === "light" ? "light" : "dark";
  const canvasBg = tk.surface.app;

  const {
    wrapRef,
    canvasRef,
    canvasHostRef,
    input,
    repulsionPercent,
    setRepulsionPercent,
    canvasLabelMode,
    setCanvasLabelMode,
    hoverNeighborsLabels,
    setHoverNeighborsLabels,
    pinnedNodeCount,
    handleToolbarResetZoom,
    applyFit,
    handleRestart,
    handleUnpinAll,
    handleCenter,
    handleApplyViewPreset,
    showDenseLabelHint,
    dismissDenseHint,
    contextMenu,
    closeContextMenu,
    runFitNodeSubset,
    centerViewportOnNode,
    handleCanvasDoubleClick,
    handleCanvasContextMenu,
    edgeLegendTypes,
    onSelectNode: onSelectNodeFromController,
  } = useGraphCanvasMvpController({
    graph,
    selectedNodeId,
    selectedEdgeId,
    onSelectNode,
    onSelectEdge,
    layoutMode,
    onCanvasLayoutModeChange,
    onAggregatorExpand,
    searchMatchIds,
    searchQuery,
    centerRequestNonce,
    centerRequestNodeId,
    graphColorBy,
    graphCommunityHulls,
    nodeCommunityMap,
    t,
    appearance,
    canvasBg,
  });

  if (graph.nodes.length === 0) {
    return <GraphCanvasEmptyState tk={tk} message={t("graph.canvas.empty")} />;
  }

  return (
    <Box
      ref={wrapRef}
      component="section"
      role="region"
      aria-label={t("graph.canvas.regionAria")}
      tabIndex={0}
      sx={{ width: "100%", flex: 1, minHeight: 0, display: "flex", flexDirection: "column", borderRadius: "6px", border: `1px solid ${tk.border.default}`, overflow: "hidden", backgroundColor: tk.surface.panel, outline: "none" }}
    >
      <GraphCanvasViewToolbar
        t={t}
        layoutMode={layoutMode}
        repulsionPercent={repulsionPercent}
        onRepulsionChange={setRepulsionPercent}
        graphColorBy={graphColorBy}
        onGraphColorByChange={onGraphColorByChange || (() => {})}
        graphCommunityHulls={graphCommunityHulls}
        onGraphCommunityHullsChange={onGraphCommunityHullsChange || (() => {})}
        canvasLabelMode={canvasLabelMode}
        onCanvasLabelModeChange={setCanvasLabelMode}
        hoverNeighborsLabels={hoverNeighborsLabels}
        onHoverNeighborsLabelsChange={setHoverNeighborsLabels}
        onFit={() => applyFit("auto")}
        onResetZoom={handleToolbarResetZoom}
        onCenterSelection={handleCenter}
        centerSelectionDisabled={!selectedNodeId}
        onRestartForce={handleRestart}
        onUnpinAll={handleUnpinAll}
        unpinDisabled={pinnedNodeCount === 0}
        hideViewControls
        onApplyViewPreset={handleApplyViewPreset}
      />
      {showDenseLabelHint ? (
        <GraphCanvasDenseLabelHint
          message={t("graph.canvasLabels.denseHint")}
          switchAdaptiveLabel={t("graph.canvasLabels.switchAdaptive")}
          switchInteractionLabel={t("graph.canvasLabels.switchInteraction")}
          onDismiss={dismissDenseHint}
          onSwitchAdaptive={() => setCanvasLabelMode("adaptive")}
          onSwitchInteraction={() => setCanvasLabelMode("interaction")}
        />
      ) : null}
      <GraphCanvasNodeContextMenu
        open={Boolean(contextMenu)}
        anchor={contextMenu}
        onClose={closeContextMenu}
        onFit={(nid) => runFitNodeSubset(nid)}
        onCenter={(nid) => centerViewportOnNode(nid)}
        onSelectNode={(nid) => onSelectNodeFromController?.(nid)}
        labels={{
          fit: t("graph.canvas.contextFit"),
          center: t("graph.canvas.contextCenter"),
          copyId: t("graph.canvas.contextCopyId"),
        }}
      />
      <Box ref={canvasHostRef} sx={{ flex: 1, minHeight: MIN_CANVAS_HEIGHT, position: "relative" }}>
        <canvas
          ref={canvasRef}
          onPointerDown={input.handlePointerDown}
          onPointerMove={input.handlePointerMove}
          onPointerLeave={input.handlePointerLeave}
          onPointerUp={input.handlePointerUp}
          onPointerCancel={input.handlePointerUp}
          onDoubleClick={handleCanvasDoubleClick}
          onContextMenu={handleCanvasContextMenu}
          style={{ display: "block", width: "100%", height: "100%", cursor: input.canvasCursor, touchAction: "none", verticalAlign: "top" }}
        />
        <GraphCanvasViewportControls
          t={t}
          onFit={() => applyFit("auto")}
          onResetZoom={handleToolbarResetZoom}
          onCenterSelection={handleCenter}
          centerSelectionDisabled={!selectedNodeId}
        />
        <GraphCanvasEdgeTypeLegend
          edgeTypes={edgeLegendTypes}
          title={t("graph.canvas.edgeLegendTitle")}
          formatEdgeType={(tp) => localizeEdgeType({ type: tp, raw: {} }, t)}
          borderColor={tk.border.default}
          panelBg={tk.surface.panel}
          textMuted={tk.text.muted}
          textSecondary={tk.text.secondary}
        />
      </Box>
    </Box>
  );
}
