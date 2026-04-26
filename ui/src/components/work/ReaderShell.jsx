import React from "react";
import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";

/**
 * Two-column reader layout on lg+; single column on narrow viewports (rail below main).
 * @param {{ main: React.ReactNode, rail: React.ReactNode }} props
 */
export default function ReaderShell({ main, rail }) {
  const theme = useTheme();
  const isLgUp = useMediaQuery(theme.breakpoints.up("lg"));

  if (isLgUp) {
    return (
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr) minmax(240px, 280px)",
          gap: 3,
          alignItems: "start",
        }}
      >
        <Box sx={{ minWidth: 0 }}>{main}</Box>
        <Box sx={{ position: "sticky", top: (theme) => theme.spacing(2), alignSelf: "start" }}>{rail}</Box>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box sx={{ minWidth: 0, order: 1 }}>{main}</Box>
      <Box sx={{ order: 2 }}>{rail}</Box>
    </Box>
  );
}
