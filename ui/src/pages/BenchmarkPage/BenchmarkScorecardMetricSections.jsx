import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

/**
 * Renders key/value rows for secondary and diagnostic scorecard buckets from the API.
 *
 * @param {{
 *   titleSecondary: string,
 *   titleDiagnostic: string,
 *   secondary: Record<string, unknown>,
 *   diagnostic: Record<string, unknown>,
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 * }} props
 */
export default function BenchmarkScorecardMetricSections({ titleSecondary, titleDiagnostic, secondary, diagnostic, tk }) {
  /* Omit null/undefined/empty string; keep false and 0. */
  const secEntries = Object.entries(secondary || {}).filter(([, v]) => v != null && v !== "");
  const diagEntries = Object.entries(diagnostic || {}).filter(([, v]) => v != null && v !== "");
  if (!secEntries.length && !diagEntries.length) return null;
  return (
    <Box sx={{ mt: 1.5, display: "grid", gap: 1.5 }}>
      {secEntries.length > 0 ? (
        <Box>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: tk.text.primary }}>{titleSecondary}</Typography>
          <Box
            component="ul"
            sx={{ m: 0, mt: 0.75, pl: 2, listStyle: "disc", color: tk.text.secondary, fontSize: "0.75rem", lineHeight: 1.5 }}
          >
            {secEntries.map(([k, v]) => (
              <li key={k}>
                <Typography component="span" sx={{ color: tk.text.muted }}>{`${k}: `}</Typography>
                <Typography component="span" sx={{ color: tk.text.primary }}>{String(v)}</Typography>
              </li>
            ))}
          </Box>
        </Box>
      ) : null}
      {diagEntries.length > 0 ? (
        <Box>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: tk.text.primary }}>{titleDiagnostic}</Typography>
          <Box
            component="ul"
            sx={{ m: 0, mt: 0.75, pl: 2, listStyle: "disc", color: tk.text.secondary, fontSize: "0.75rem", lineHeight: 1.5 }}
          >
            {diagEntries.map(([k, v]) => (
              <li key={k}>
                <Typography component="span" sx={{ color: tk.text.muted }}>{`${k}: `}</Typography>
                <Typography component="span" sx={{ color: tk.text.primary }}>{String(v)}</Typography>
              </li>
            ))}
          </Box>
        </Box>
      ) : null}
    </Box>
  );
}
