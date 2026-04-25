import React, { useCallback } from "react";
import Box from "@mui/material/Box";

import GraphDetailPanel from "./GraphDetailPanel.jsx";
import { clampGraphDetailColumnPx } from "./graphDetailColumnWidth.js";

export default function GraphSidePanel({
  standalone,
  visible,
  selectedNode,
  selectedEdge,
  relatedEdges,
  relatedEdgeRows,
  selectedEdgeReadable,
  graphMeta,
  onSelectNode,
  onSelectEdge,
  onExpandWorkspaceNeighbors,
  expandWorkspaceNeighborsBusy,
  mode,
  width,
  onWidthChange,
}) {
  const handleResizeStart = useCallback(
    (e) => {
      if (e.button !== 0) return;
      e.preventDefault();
      const el = e.currentTarget;
      const pointerId = e.pointerId;
      try {
        el.setPointerCapture(pointerId);
      } catch {
        /* ignore */
      }
      const startX = e.clientX;
      const startW = width;
      const prevCursor = document.body.style.cursor;
      const prevUserSelect = document.body.style.userSelect;
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      const onMove = (ev) => onWidthChange(clampGraphDetailColumnPx(startW + (ev.clientX - startX)));
      const onEnd = () => {
        document.body.style.cursor = prevCursor;
        document.body.style.userSelect = prevUserSelect;
        try {
          el.releasePointerCapture(pointerId);
        } catch {
          /* ignore */
        }
        el.removeEventListener("pointermove", onMove);
        el.removeEventListener("pointerup", onEnd);
        el.removeEventListener("pointercancel", onEnd);
      };
      el.addEventListener("pointermove", onMove);
      el.addEventListener("pointerup", onEnd);
      el.addEventListener("pointercancel", onEnd);
    },
    [onWidthChange, width],
  );

  if (!visible) return null;

  return (
    <>
      {standalone ? (
        <Box
          onPointerDown={handleResizeStart}
          sx={{
            display: { xs: "none", md: "block" },
            width: 6,
            flexShrink: 0,
            cursor: "col-resize",
            alignSelf: "stretch",
            touchAction: "none",
            borderRadius: "2px",
            backgroundColor: "rgba(255,255,255,0.06)",
            "&:hover": { backgroundColor: "rgba(255,255,255,0.12)" },
          }}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize graph and detail panels"
        />
      ) : null}
      <Box sx={{ minWidth: 0, minHeight: standalone ? 0 : { xs: 220, md: 400 }, display: "flex", flexDirection: "column" }}>
        <GraphDetailPanel
          selectedNode={selectedNode}
          selectedEdge={selectedEdge}
          relatedEdges={relatedEdges}
          relatedEdgeRows={relatedEdgeRows}
          selectedEdgeReadable={selectedEdgeReadable}
          graphMeta={graphMeta}
          onSelectNode={onSelectNode}
          onSelectEdge={onSelectEdge}
          onExpandWorkspaceNeighbors={onExpandWorkspaceNeighbors}
          expandWorkspaceNeighborsBusy={expandWorkspaceNeighborsBusy}
          mode={mode}
        />
      </Box>
    </>
  );
}
