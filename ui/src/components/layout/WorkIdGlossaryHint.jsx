import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { WORK_ID_GLOSSARY_COPY } from "./workIdGlossaryCopy.js";

/**
 * @param {{
 *   variant: "workspace" | "corpus" | "ask" | "graph",
 *   sx?: object,
 * }} props
 */
export default function WorkIdGlossaryHint({ variant, sx }) {
  return (
    <Box component="span" sx={sx}>
      <Typography
        component="span"
        sx={{ fontSize: "inherit", color: "inherit", lineHeight: "inherit" }}
      >
        {variant === "workspace" ? (
          <>
            Open a work and switch tabs without leaving context. <strong>work_id</strong> is the indexed paper id; the{" "}
            <strong>workspace session</strong> ties Reader, Graph, Ask, and Evidence to that paper.
          </>
        ) : variant === "corpus" ? (
          <>
            {WORK_ID_GLOSSARY_COPY.corpusIntroPrefix}{" "}
            <code style={{ color: "rgba(129,140,248,0.95)" }}>GET /v1/works</code>
            {". "}
            {WORK_ID_GLOSSARY_COPY.corpusIntroRest}
          </>
        ) : variant === "ask" ? (
          <>
            <code style={{ color: "rgba(129,140,248,0.95)" }}>work_id</code> {WORK_ID_GLOSSARY_COPY.askOptionalWorkRest}
          </>
        ) : (
          <>
            This graph is loaded for the active <code style={{ color: "rgba(129,140,248,0.95)" }}>work_id</code>.{" "}
            {WORK_ID_GLOSSARY_COPY.graphScopedRest}
          </>
        )}
      </Typography>
    </Box>
  );
}
