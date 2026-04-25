import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

function statusColor(status) {
  if (status === "completed") return "rgba(129,140,248,0.95)";
  if (status === "failed") return "rgba(239,68,68,0.9)";
  if (status === "running") return "rgba(255,255,255,0.9)";
  return "rgba(255,255,255,0.5)";
}

function statusSymbol(status) {
  if (status === "completed") return "✓";
  if (status === "failed") return "×";
  if (status === "running") return "●";
  return "○";
}

function formatMetrics(metrics) {
  const entries = Object.entries(metrics || {});
  if (!entries.length) return "";
  return entries.map(([k, v]) => `${k}: ${String(v)}`).join(", ");
}

export default function IngestStageStepper({ stages = [] }) {
  if (!Array.isArray(stages) || !stages.length) return null;

  return (
    <Box sx={{ mt: 1, display: "flex", flexDirection: "column", gap: 0.75 }}>
      {stages.map((item) => {
        const color = statusColor(item.status);
        const metricsText = formatMetrics(item.metrics);
        return (
          <Box
            key={`${item.name}-${item.started_at || ""}`}
            sx={{
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "6px",
              p: 0.75,
              backgroundColor: "rgba(255,255,255,0.02)",
            }}
          >
            <Typography sx={{ fontSize: "0.72rem", color, fontWeight: 600 }}>
              {statusSymbol(item.status)} {String(item.name || "stage")}
              {Number.isFinite(item.duration_ms) ? ` · ${Math.max(0, Number(item.duration_ms))} ms` : ""}
            </Typography>
            {metricsText ? (
              <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.6)", mt: 0.25 }}>{metricsText}</Typography>
            ) : null}
            {item.error ? (
              <Typography sx={{ fontSize: "0.68rem", color: "rgba(239,68,68,0.85)", mt: 0.25 }}>
                {String(item.error)}
              </Typography>
            ) : null}
          </Box>
        );
      })}
    </Box>
  );
}
