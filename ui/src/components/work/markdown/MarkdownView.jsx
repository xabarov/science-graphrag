import React, { lazy, Suspense } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";

const MarkdownViewCore = lazy(() => import("./MarkdownViewCore.jsx"));

/**
 * Lazy-loaded markdown body (keeps initial chunk smaller).
 * @param {{ markdown: string, "data-testid"?: string }} props
 */
export default function MarkdownView({ markdown = "", "data-testid": dataTestId }) {
  return (
    <Suspense
      fallback={
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 1.5 }}>
          <CircularProgress size={22} sx={{ color: "rgba(129,140,248,0.9)" }} />
        </Box>
      }
    >
      <MarkdownViewCore markdown={markdown} data-testid={dataTestId} />
    </Suspense>
  );
}
