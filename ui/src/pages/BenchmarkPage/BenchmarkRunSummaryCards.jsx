import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

function SummaryCard({ label, value, tone = "default" }) {
  const accent =
    tone === "danger"
      ? "rgba(239, 68, 68, 0.8)"
      : tone === "primary"
        ? "rgba(129, 140, 248, 0.95)"
        : "rgba(255,255,255,0.9)";
  return (
    <Box
      sx={{
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 1.5,
        padding: 1.5,
        backgroundColor: "#1a1a1a",
      }}
    >
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.6)" }}>{label}</Typography>
      <Typography sx={{ fontWeight: 600, color: accent }}>{value}</Typography>
    </Box>
  );
}

export default function BenchmarkRunSummaryCards({ run }) {
  const summary = run?.summary || {};
  const family = run?.benchmark_family || "layer1";

  return (
    <Box sx={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: 1 }}>
      <SummaryCard label="Status" value={run?.status || "-"} tone={run?.status === "failed" ? "danger" : "primary"} />
      <SummaryCard label="Cases" value={summary.case_count ?? run?.progress?.total ?? 0} />
      <SummaryCard label="Passed" value={summary.pass_count ?? 0} tone="primary" />
      <SummaryCard label="Failed" value={summary.fail_count ?? 0} tone={summary.fail_count ? "danger" : "default"} />
      <SummaryCard
        label={family === "layer2" ? "Avg recall" : "Avg names_f1"}
        value={
          family === "layer2"
            ? (summary.avg_layer2_recall_ratio ?? 0).toFixed(3)
            : (summary.avg_names_f1 ?? 0).toFixed(3)
        }
      />
    </Box>
  );
}
