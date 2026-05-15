import React from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { formatInspectorIssueLine } from "./benchmarkCaseInspectorFormatting.js";

/**
 * Compare-mode banner + headline / issues alert.
 *
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   compareContext: { baselineRunId: string; metric: string } | null,
 *   headline: string,
 *   headlineSeverity: "error" | "warning" | "success",
 *   issues: unknown[],
 *   t: (key: string, vars?: Record<string, string | number>) => string,
 * }} props
 */
export default function BenchmarkCaseInspectorHeadlineSection({
  tk,
  compareContext,
  headline,
  headlineSeverity,
  issues,
  t,
}) {
  return (
    <>
      {compareContext ? (
        <Alert
          severity="info"
          sx={{
            fontSize: "0.8125rem",
            backgroundColor: tk.surface.subtle,
            border: `1px solid ${tk.border.default}`,
            color: tk.text.primary,
            "& .MuiAlert-icon": { color: tk.accent.fg },
          }}
        >
          <Typography sx={{ fontSize: "0.8125rem", lineHeight: 1.5 }}>
            {t("benchmark.inspector.compareBanner", {
              metric: compareContext.metric,
              baseline: compareContext.baselineRunId.slice(0, 8),
            })}
          </Typography>
        </Alert>
      ) : null}

      <Alert
        severity={headlineSeverity === "success" ? "success" : headlineSeverity}
        sx={{
          fontSize: "0.8125rem",
          "& .MuiAlert-message": { width: "100%" },
        }}
      >
        <Typography sx={{ fontWeight: 600, mb: issues.length ? 0.75 : 0 }}>{headline}</Typography>
        {issues.length ? (
          <Box component="ul" sx={{ m: 0, pl: 2.5, mb: 0 }}>
            {issues.map((issue, idx) => (
              <Typography key={idx} component="li" sx={{ fontSize: "0.8125rem", lineHeight: 1.45 }}>
                {formatInspectorIssueLine(/** @type {Record<string, unknown>} */ (issue), t)}
              </Typography>
            ))}
          </Box>
        ) : null}
      </Alert>
    </>
  );
}
