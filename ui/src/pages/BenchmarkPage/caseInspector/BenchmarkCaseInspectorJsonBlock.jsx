import React from "react";
import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";

export default function BenchmarkCaseInspectorJsonBlock({ value }) {
  const tk = useTheme().appTokens;
  return (
    <Box
      component="pre"
      sx={{
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        maxHeight: 360,
        overflow: "auto",
        margin: 0,
        fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
        fontSize: "12px",
        color: tk.text.primary,
      }}
    >
      {JSON.stringify(value, null, 2)}
    </Box>
  );
}
