import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

/**
 * @param {{
 *   selectedNode: { id: string, label: string, type: string, raw: object } | null,
 *   relatedEdges: Array<{ id: string, source: string, target: string, type: string, raw: object }>,
 *   mode?: "embedded" | "standalone",
 * }} props
 */
export default function GraphDetailPanel({ selectedNode, relatedEdges, mode = "embedded" }) {
  const compact = mode === "embedded";

  return (
    <Box
      sx={{
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
        p: compact ? 1.5 : 2,
        minHeight: compact ? 240 : 320,
      }}
    >
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 1 }}>Details</Typography>

      {!selectedNode ? (
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>
          Select a node to inspect its payload and related edges.
        </Typography>
      ) : (
        <>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.92)" }}>{selectedNode.type}</Typography>
          <Typography sx={{ fontSize: "0.9375rem", fontWeight: 600, color: "rgba(255,255,255,0.9)", mt: 0.25 }}>
            {selectedNode.label}
          </Typography>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.5, fontFamily: "monospace" }}>
            {selectedNode.id}
          </Typography>

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.75 }}>Related edges</Typography>
          {relatedEdges.length === 0 ? (
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>No connected edges.</Typography>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
              {relatedEdges.map((edge) => (
                <Box key={edge.id} sx={{ p: 1, borderRadius: "6px", backgroundColor: "#141414", border: "1px solid rgba(255,255,255,0.06)" }}>
                  <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.92)" }}>{edge.type}</Typography>
                  <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)", mt: 0.25 }}>
                    {edge.source} → {edge.target}
                  </Typography>
                </Box>
              ))}
            </Box>
          )}

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.75 }}>Raw payload</Typography>
          <Typography
            component="pre"
            sx={{
              m: 0,
              p: 1.25,
              borderRadius: "6px",
              backgroundColor: "#141414",
              border: "1px solid rgba(255,255,255,0.06)",
              fontSize: "0.75rem",
              color: "rgba(255,255,255,0.72)",
              overflow: "auto",
              maxHeight: compact ? 220 : 320,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {JSON.stringify(selectedNode.raw, null, 2)}
          </Typography>
        </>
      )}
    </Box>
  );
}
