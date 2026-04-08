import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

/**
 * Lightweight graph overview without extra dependencies.
 * @param {{
 *   graph: { nodes: Array<{id: string, label: string, type: string}>, edges: Array<{id: string, source: string, target: string, type: string}> },
 *   selectedNodeId: string,
 *   onSelectNode: (nodeId: string) => void,
 *   mode?: "embedded" | "standalone",
 * }} props
 */
export default function GraphVisualization({ graph, selectedNodeId, onSelectNode, mode = "embedded" }) {
  const compact = mode === "embedded";

  return (
    <Box
      sx={{
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
        p: compact ? 1.5 : 2,
      }}
    >
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 1 }}>
        Node map. Select a node to inspect related edges and raw payload.
      </Typography>

      <Box sx={{ display: "grid", gridTemplateColumns: compact ? "repeat(auto-fill, minmax(160px, 1fr))" : "repeat(auto-fill, minmax(180px, 1fr))", gap: 1 }}>
        {graph.nodes.map((node) => {
          const active = node.id === selectedNodeId;
          return (
            <Box
              key={node.id}
              role="button"
              tabIndex={0}
              onClick={() => onSelectNode(node.id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectNode(node.id);
                }
              }}
              sx={{
                p: 1.25,
                borderRadius: "6px",
                cursor: "pointer",
                border: active ? "1px solid rgba(99, 102, 241, 0.42)" : "1px solid rgba(255,255,255,0.08)",
                backgroundColor: active ? "rgba(99, 102, 241, 0.12)" : "#141414",
                transition: "all 0.15s ease",
                "&:hover": {
                  borderColor: "rgba(255,255,255,0.18)",
                  backgroundColor: active ? "rgba(99, 102, 241, 0.14)" : "rgba(255,255,255,0.04)",
                },
              }}
            >
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.92)", mb: 0.5 }}>{node.type}</Typography>
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)", fontWeight: 600, lineHeight: 1.35 }}>
                {node.label}
              </Typography>
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.5, fontFamily: "monospace", wordBreak: "break-word" }}>
                {node.id}
              </Typography>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}
