import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

/**
 * @param {{ summary?: Record<string, unknown>, result?: Record<string, unknown> }} props
 */
export default function CompareTabSummarySection({ summary, result }) {
  if (!summary) return null;
  return (
    <>
      <Box sx={{ mb: 2, display: "flex", flexWrap: "wrap", gap: 2 }}>
        <Box
          sx={{
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 1.5,
            px: 1.5,
            py: 1,
            backgroundColor: "#1a1a1a",
          }}
        >
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Regressions</Typography>
          <Typography sx={{ fontWeight: 600 }}>{summary.regression_count}</Typography>
        </Box>
        <Box
          sx={{
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 1.5,
            px: 1.5,
            py: 1,
            backgroundColor: "#1a1a1a",
          }}
        >
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Improvements</Typography>
          <Typography sx={{ fontWeight: 600 }}>{summary.improvement_count}</Typography>
        </Box>
        <Box
          sx={{
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 1.5,
            px: 1.5,
            py: 1,
            backgroundColor: "#1a1a1a",
          }}
        >
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Unchanged metric rows</Typography>
          <Typography sx={{ fontWeight: 600 }}>{summary.unchanged_count}</Typography>
        </Box>
        <Box
          sx={{
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 1.5,
            px: 1.5,
            py: 1,
            backgroundColor: "#1a1a1a",
          }}
        >
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Missing in current</Typography>
          <Typography sx={{ fontWeight: 600 }}>{(summary.missing_in_current || []).length}</Typography>
        </Box>
        <Box
          sx={{
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 1.5,
            px: 1.5,
            py: 1,
            backgroundColor: "#1a1a1a",
          }}
        >
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Added in current</Typography>
          <Typography sx={{ fontWeight: 600 }}>{(summary.added_in_current || []).length}</Typography>
        </Box>
      </Box>

      {summary?.missing_in_current?.length ? (
        <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem", mb: 1 }}>
          Missing in current: {summary.missing_in_current.join(", ")}
        </Typography>
      ) : null}
      {summary?.added_in_current?.length ? (
        <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem", mb: 1 }}>
          Added in current: {summary.added_in_current.join(", ")}
        </Typography>
      ) : null}

      {result?.skipped_baseline?.length ? (
        <Typography sx={{ color: "rgba(255,200,100,0.85)", fontSize: "0.8125rem", mb: 1 }}>
          Skipped baseline cases:{" "}
          {result.skipped_baseline.map((s) => `${s.case_id} (${s.reason})`).join("; ")}
        </Typography>
      ) : null}
      {result?.skipped_current?.length ? (
        <Typography sx={{ color: "rgba(255,200,100,0.85)", fontSize: "0.8125rem", mb: 1 }}>
          Skipped current cases:{" "}
          {result.skipped_current.map((s) => `${s.case_id} (${s.reason})`).join("; ")}
        </Typography>
      ) : null}
    </>
  );
}
