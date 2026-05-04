import React, { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import Tooltip from "@mui/material/Tooltip";
import UnfoldMoreOutlinedIcon from "@mui/icons-material/UnfoldMoreOutlined";

/**
 * Footer diagnostics for graph layer counts. When all four layers match in pairs, show one compact
 * line with an affordance to expand the full four-metric breakdown.
 *
 * @param {{
 *   t: (k: string, v?: Record<string, string | number>) => string,
 *   graph: { nodeCount: number, edgeCount: number },
 *   projectedGraph: { nodeCount: number, edgeCount: number },
 *   visibleGraph: { nodeCount: number, edgeCount: number },
 *   displayGraph: { nodeCount: number, edgeCount: number },
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 * }} props
 */
export default function GraphWorkspaceLayerCountsFooter({
  t,
  tk,
  graph,
  projectedGraph,
  visibleGraph,
  displayGraph,
}) {
  const [showAllLayers, setShowAllLayers] = useState(false);

  const layersAligned = useMemo(() => {
    const sn = graph.nodeCount;
    const se = graph.edgeCount;
    const pn = projectedGraph.nodeCount;
    const pe = projectedGraph.edgeCount;
    const vn = visibleGraph.nodeCount;
    const ve = visibleGraph.edgeCount;
    const dn = displayGraph.nodeCount;
    const de = displayGraph.edgeCount;
    return sn === pn && se === pe && vn === dn && ve === de;
  }, [graph, projectedGraph, visibleGraph, displayGraph]);

  const compactLabel = t("graph.layerCounts.compactSame", {
    n: String(displayGraph.nodeCount),
    e: String(displayGraph.edgeCount),
  });

  const detailRows = useMemo(
    () => [
      { key: "server", text: t("graph.layerCounts.server", { n: String(graph.nodeCount), e: String(graph.edgeCount) }) },
      {
        key: "projected",
        text: t("graph.layerCounts.projected", { n: String(projectedGraph.nodeCount), e: String(projectedGraph.edgeCount) }),
      },
      {
        key: "visible",
        text: t("graph.layerCounts.visible", { n: String(visibleGraph.nodeCount), e: String(visibleGraph.edgeCount) }),
      },
      {
        key: "display",
        text: t("graph.layerCounts.display", { n: String(displayGraph.nodeCount), e: String(displayGraph.edgeCount) }),
      },
    ],
    [t, graph, projectedGraph, visibleGraph, displayGraph],
  );

  if (layersAligned && !showAllLayers) {
    return (
      <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5 }}>
        <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted }}>{compactLabel}</Typography>
        <Tooltip title={t("graph.layerCounts.expandLayersTooltip")}>
          <IconButton
            size="small"
            aria-label={t("graph.layerCounts.expandLayersAria")}
            onClick={() => setShowAllLayers(true)}
            sx={{ color: tk.text.faint, p: 0.25 }}
          >
            <UnfoldMoreOutlinedIcon sx={{ fontSize: "1rem" }} />
          </IconButton>
        </Tooltip>
      </Box>
    );
  }

  return (
    <Box sx={{ mt: 1 }}>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, columnGap: 1.5, rowGap: 0.5 }}>
        {detailRows.map((r) => (
          <Typography key={r.key} sx={{ fontSize: "0.72rem", color: tk.text.muted }}>
            {r.text}
          </Typography>
        ))}
      </Box>
      {layersAligned ? (
        <Typography
          component="button"
          type="button"
          onClick={() => setShowAllLayers(false)}
          sx={{
            mt: 0.5,
            display: "block",
            fontSize: "0.68rem",
            color: tk.accent.fg,
            cursor: "pointer",
            border: "none",
            background: "none",
            p: 0,
            textAlign: "left",
            textDecoration: "underline",
          }}
        >
          {t("graph.layerCounts.collapseLayers")}
        </Typography>
      ) : null}
    </Box>
  );
}
