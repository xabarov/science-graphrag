import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

export default function AgentToolTrace({ toolTrace = [] }) {
  if (!Array.isArray(toolTrace) || toolTrace.length === 0) return null;
  return (
    <Box sx={{ mt: 1, p: 1, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "rgba(0,0,0,0.2)" }}>
      {toolTrace.map((step, idx) => (
        <Box key={`${step.tool || "tool"}-${idx}`} sx={{ mb: 0.75 }}>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.85)" }}>
            {`#${step.step ?? idx + 1} ${step.tool || "tool"} · ${step.duration_ms ?? 0}ms`}
          </Typography>
          <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.5)" }}>
            {`rows=${step.row_count ?? "-"} ${step.error ? `· error=${step.error}` : ""}`}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}
