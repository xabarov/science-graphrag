import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

/**
 * @param {{ lines: string[], t: (key: string) => string }} props
 */
export default function TrustConsistencyWarningsList({ lines, t }) {
  const tk = useTheme().appTokens;
  if (!lines?.length) return null;
  return (
    <Box>
      <Typography
        sx={{
          color: tk.text.secondary,
          fontSize: "0.7rem",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.04em",
          mb: 0.5,
        }}
      >
        {t("benchmarkPage.trustDrillIn.sectionWarnings")}
      </Typography>
      <Box
        component="ul"
        sx={{
          m: 0,
          pl: 2,
          color: tk.text.primary,
          fontSize: "0.75rem",
          lineHeight: 1.45,
        }}
      >
        {lines.map((line, i) => (
          <li key={`${i}-${line.slice(0, 48)}`}>
            <Typography component="span" sx={{ fontSize: "0.75rem", color: "inherit" }}>
              {line}
            </Typography>
          </li>
        ))}
      </Box>
    </Box>
  );
}
