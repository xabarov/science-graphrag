import React, { useLayoutEffect, useMemo, useRef } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

/**
 * Lightweight graph overview without extra dependencies.
 * Keyboard: roving tabindex with Arrow keys; Enter/Space activates selection.
 * @param {{
 *   graph: { nodes: Array<{id: string, label: string, type: string}>, edges: Array<{id: string, source: string, target: string, type: string}> },
 *   selectedNodeId: string,
 *   onSelectNode: (nodeId: string) => void,
 *   mode?: "embedded" | "standalone",
 * }} props
 */
export default function GraphVisualization({ graph, selectedNodeId, onSelectNode, mode = "embedded" }) {
  const compact = mode === "embedded";
  const itemRefs = useRef(/** @type {Array<HTMLElement | null>} */ ([]));

  const activeIndex = useMemo(() => {
    const i = graph.nodes.findIndex((node) => node.id === selectedNodeId);
    return i >= 0 ? i : 0;
  }, [selectedNodeId, graph.nodes]);

  useLayoutEffect(() => {
    if (graph.nodes.length === 0) return;
    const ae = document.activeElement;
    const inGrid = itemRefs.current.some((el) => el && el === ae);
    if (inGrid) {
      itemRefs.current[activeIndex]?.focus({ preventScroll: true });
    }
  }, [activeIndex, graph.nodes.length]);

  function handleCardKeyDown(index, event) {
    const n = graph.nodes.length;
    if (n === 0) return;

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelectNode(graph.nodes[index].id);
      return;
    }
    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      const next = (index + 1) % n;
      onSelectNode(graph.nodes[next].id);
      return;
    }
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      const prev = (index - 1 + n) % n;
      onSelectNode(graph.nodes[prev].id);
    }
  }

  return (
    <Box
      component="section"
      role="region"
      aria-label="Graph node map"
      sx={{
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
        p: compact ? 1.5 : 2,
      }}
    >
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 1 }}>
        Node map. Select a node to inspect related edges and raw payload. Use arrow keys to move between nodes.
      </Typography>

      <Box sx={{ display: "grid", gridTemplateColumns: compact ? "repeat(auto-fill, minmax(160px, 1fr))" : "repeat(auto-fill, minmax(180px, 1fr))", gap: 1 }}>
        {graph.nodes.map((node, index) => {
          const active = node.id === selectedNodeId;
          return (
            <Box
              key={node.id}
              ref={(el) => {
                itemRefs.current[index] = el;
              }}
              role="button"
              tabIndex={index === activeIndex ? 0 : -1}
              aria-pressed={active}
              aria-label={`${node.type}: ${node.label}`}
              onClick={() => onSelectNode(node.id)}
              onKeyDown={(event) => handleCardKeyDown(index, event)}
              sx={{
                p: 1.25,
                borderRadius: "6px",
                cursor: "pointer",
                border: active ? "1px solid rgba(99, 102, 241, 0.42)" : "1px solid rgba(255,255,255,0.08)",
                backgroundColor: active ? "rgba(99, 102, 241, 0.12)" : "#141414",
                transition: "all 0.15s ease",
                outline: "none",
                "&:focus-visible": {
                  boxShadow: "0 0 0 1px rgba(99, 102, 241, 0.5)",
                },
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
