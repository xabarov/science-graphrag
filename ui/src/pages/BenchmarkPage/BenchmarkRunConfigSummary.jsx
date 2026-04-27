import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

function SummaryItem({ label, value }) {
  const tk = useTheme().appTokens;
  return (
    <Box
      sx={{
        border: `1px solid ${tk.border.default}`,
        borderRadius: 1.5,
        backgroundColor: tk.surface.panel,
        padding: 1,
        minWidth: 0,
      }}
    >
      <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mb: 0.25 }}>
        {label}
      </Typography>
      <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, wordBreak: "break-word" }}>
        {value || "—"}
      </Typography>
    </Box>
  );
}

export default function BenchmarkRunConfigSummary({ summary, title = "Execution summary" }) {
  const tk = useTheme().appTokens;
  if (!summary) return null;
  return (
    <Box
      sx={{
        border: `1px solid ${tk.border.default}`,
        borderRadius: 1.5,
        backgroundColor: tk.surface.panel,
        padding: 1.5,
      }}
    >
      <Typography sx={{ fontWeight: 600, mb: 1 }}>{title}</Typography>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 1,
        }}
      >
        <SummaryItem label="Family" value={summary.family} />
        <SummaryItem label="Scope" value={summary.scopeLabel} />
        <SummaryItem label="Status" value={summary.status} />
        <SummaryItem label="Model profile" value={summary.modelProfile} />
        <SummaryItem label="Effective model" value={summary.effectiveModelId} />
        <SummaryItem label="Gold source" value={summary.goldSource} />
        <SummaryItem label="Threshold" value={summary.thresholdProfile} />
        <SummaryItem label="Base URL override" value={summary.baseUrlOverride || "default backend"} />
        <SummaryItem label="API key env var" value={summary.apiKeyEnvName || "default backend"} />
      </Box>
    </Box>
  );
}
