import React from "react";
import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";

/**
 * Dense horizontal toolbar for icon actions (researcher workflow).
 *
 * @param {{
 *   children?: React.ReactNode,
 *   groups?: React.ReactNode[][],
 *   tail?: React.ReactNode,
 *   sx?: object,
 * }} props
 *
 * Either pass `groups` as array of rows of nodes, or `children` as a flat row.
 */
export default function PageActionToolbar({ children, groups, tail, sx }) {
  const tk = useTheme().appTokens;
  const rows = groups && groups.length > 0 ? groups : children ? [React.Children.toArray(children).filter(Boolean)] : [];

  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: 0.75,
        mt: 1.25,
        minHeight: 36,
        ...(sx || {}),
      }}
    >
      {rows.map((row, gi) => (
        <React.Fragment key={gi}>
          {gi > 0 ? (
            <Box
              component="span"
              sx={{
                width: "1px",
                height: 22,
                bgcolor: tk.border.strong,
                alignSelf: "center",
                mx: 0.25,
              }}
            />
          ) : null}
          <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5 }}>{row}</Box>
        </React.Fragment>
      ))}
      {tail ? (
        <>
          <Box sx={{ flex: 1, minWidth: 8 }} />
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>{tail}</Box>
        </>
      ) : null}
    </Box>
  );
}
