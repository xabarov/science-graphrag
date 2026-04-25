import React from "react";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

import { getScienceGraphLegendNodeChipSx, getScienceGraphNodeTypeIcon } from "./graphCanvasStyle.js";
import { collectGraphTypeLegend } from "./graphTypeLegend.js";

const NODE_KIND_GROUPS = [
  {
    group: "Works",
    kinds: ["Work", "WorkInternal", "WorkExternal"],
    description: "Research papers",
  },
  {
    group: "Semantic",
    kinds: ["Method", "Dataset"],
    description: "Methods & Datasets",
  },
  {
    group: "People",
    kinds: ["Author", "AuthorshipReification"],
    description: "Authors & Authorship",
  },
  {
    group: "Context",
    kinds: ["Venue", "Institution"],
    description: "Venues & Institutions",
  },
];

/**
 * Compact legend of node and edge `type` values in the current display graph.
 * @param {{ graph: { nodes: Array<object>, edges: Array<object> } }} props
 */
export default function GraphTypeLegend({ graph }) {
  const { nodeTypes, edgeTypes } = collectGraphTypeLegend(graph);
  const presentKinds = new Set(
    (graph?.nodes || []).map((n) => {
      const kind = n?.nodeKind ?? n?.node_kind ?? n?.type;
      return kind != null && String(kind).trim() ? String(kind) : "Node";
    }),
  );
  const groupedNodeKinds = NODE_KIND_GROUPS.map((entry) => ({
    ...entry,
    kinds: entry.kinds.filter((kind) => presentKinds.has(kind)),
  })).filter((entry) => entry.kinds.length > 0);
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
            {groupedNodeKinds.map(({ group, kinds }) => (
              <React.Fragment key={`grp-${group}`}>
                <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.45)", mr: 0.25 }}>
                  {group}
                </Typography>
                {kinds.map((kind) => {
                  const KindIcon = getScienceGraphNodeTypeIcon(kind);
                  const dimInternal = kind === "WorkInternal";
                  return (
                    <Chip
                      key={`n-${group}-${kind}`}
                      icon={
                        KindIcon ? (
                          <KindIcon
                            sx={{
                              fontSize: "0.9rem !important",
                              color: "inherit !important",
                              opacity: dimInternal ? 0.65 : 0.95,
                            }}
                          />
                        ) : undefined
                      }
                      label={kind}
                      size="small"
                      sx={{
                        ...getScienceGraphLegendNodeChipSx(kind),
                        "& .MuiChip-icon": { marginLeft: "6px" },
                      }}
                    />
                  );
                })}
              </React.Fragment>
            ))}
          </>
        ) : null}
        {edgeTypes.length > 0 ? (
          <>
            <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.4)", ml: nodeTypes.length ? 1 : 0, mr: 0.25 }}>
              Edges
            </Typography>
            {edgeTypes.map((edgeType) => (
              <Chip
                key={`e-${edgeType}`}
                icon={<ArrowForwardIcon sx={{ fontSize: "0.65rem !important", color: "rgba(255,255,255,0.45) !important" }} />}
                label={edgeType}
                size="small"
                variant="outlined"
                sx={{
                  height: 22,
                  fontSize: "0.75rem",
                  borderColor: "rgba(255,255,255,0.14)",
                  color: "rgba(255,255,255,0.65)",
                  "& .MuiChip-icon": { marginLeft: "6px" },
                }}
              />
            ))}
          </>
        ) : null}
      </Box>
    </Box>
  );
}
