import React from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

import { getScienceGraphLegendNodeChipSx } from "./graphCanvasStyle.js";
import { collectGraphTypeLegend, collectGraphTypeLegendByKind } from "./graphTypeLegend.js";

/**
 * Compact legend of node and edge `type` values in the current display graph.
 * @param {{ graph: { nodes: Array<object>, edges: Array<object> } }} props
 */
export default function GraphTypeLegend({ graph }) {
  const { nodeTypes, edgeTypes } = collectGraphTypeLegend(graph);
  const groupedNodeKinds = collectGraphTypeLegendByKind(graph);
  if (nodeTypes.length === 0 && edgeTypes.length === 0) {
    return null;
  }

  return (
    <Box
      sx={{
        mb: { xs: 1, sm: 1.5 },
        p: { xs: 0.75, sm: 1 },
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "rgba(255,255,255,0.02)",
      }}
    >
      <Typography
        sx={{
          fontSize: { xs: "0.7rem", sm: "0.75rem" },
          fontWeight: 600,
          color: "rgba(255,255,255,0.55)",
          mb: 0.75,
        }}
      >
        Types in view
      </Typography>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: { xs: 0.5, sm: 0.75 },
          alignItems: "center",
        }}
      >
        {nodeTypes.length > 0 ? (
          <>
            <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.4)", mr: 0.25 }}>Nodes</Typography>
            {Object.entries(groupedNodeKinds).map(([group, kinds]) => (
              <React.Fragment key={`grp-${group}`}>
                <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.45)", mr: 0.25 }}>
                  {group}
                </Typography>
                {kinds.map((t) => (
                  <Chip
                    key={`n-${group}-${t}`}
                    label={t}
                    size="small"
                    sx={getScienceGraphLegendNodeChipSx(t)}
                  />
                ))}
              </React.Fragment>
            ))}
          </>
        ) : null}
        {edgeTypes.length > 0 ? (
          <>
            <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.4)", ml: nodeTypes.length ? 1 : 0, mr: 0.25 }}>
              Edges
            </Typography>
            {edgeTypes.map((t) => (
              <Chip
                key={`e-${t}`}
                label={t}
                size="small"
                variant="outlined"
                sx={{
                  height: 22,
                  fontSize: "0.75rem",
                  borderColor: "rgba(255,255,255,0.14)",
                  color: "rgba(255,255,255,0.65)",
                }}
              />
            ))}
          </>
        ) : null}
      </Box>
    </Box>
  );
}
