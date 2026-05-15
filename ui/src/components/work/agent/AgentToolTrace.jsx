import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { formatToolTraceErrorLine } from "./toolTraceError.js";

/**
 * @param {{
 *   toolTrace?: Array<Record<string, unknown>>,
 *   t?: (key: string, vars?: Record<string, string>) => string,
 * }} props
 */
export default function AgentToolTrace({ toolTrace = [], t }) {
  if (!Array.isArray(toolTrace) || toolTrace.length === 0) return null;
  const hasT = typeof t === "function";
  return (
    <Box sx={{ mt: 1, p: 1, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "rgba(0,0,0,0.2)" }}>
      {toolTrace.map((step, idx) => (
        <Box key={`${step.tool || "tool"}-${idx}`} sx={{ mb: 0.75 }}>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.85)" }}>
            {`#${step.step ?? idx + 1} ${step.tool || "tool"} · ${step.duration_ms ?? 0}ms`}
          </Typography>
          <Typography
            data-testid={step.error ? `agent-tool-trace-error-${idx}` : undefined}
            sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.5)" }}
          >
            {`rows=${step.row_count ?? "-"} `}
            {step.error
              ? hasT
                ? `· ${formatToolTraceErrorLine(t, String(step.error))}`
                : `· error=${step.error}`
              : ""}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}
