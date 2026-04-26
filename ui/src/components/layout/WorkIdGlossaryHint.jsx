import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../i18n/useI18n.js";

/**
 * @param {{
 *   variant: "workspace" | "corpus" | "ask" | "graph",
 *   sx?: object,
 * }} props
 */
export default function WorkIdGlossaryHint({ variant, sx }) {
  const { t } = useI18n();
  return (
    <Box component="span" sx={sx}>
      <Typography
        component="span"
        sx={{ fontSize: "inherit", color: "inherit", lineHeight: "inherit" }}
      >
        {variant === "workspace" ? (
          <>
            {t("workIdHint.workspace.p1")} <strong>work_id</strong> {t("workIdHint.workspace.p2")}{" "}
            <strong>{t("workIdHint.workspace.session")}</strong> {t("workIdHint.workspace.p3")}
          </>
        ) : variant === "corpus" ? (
          <>
            {t("workIdHint.corpus.prefix")}{" "}
            <code style={{ color: "rgba(129,140,248,0.95)" }}>GET /v1/works</code>
            {". "}
            {t("workIdHint.corpus.rest")}
          </>
        ) : variant === "ask" ? (
          <>
            <code style={{ color: "rgba(129,140,248,0.95)" }}>work_id</code> {t("workIdHint.ask.rest")}
          </>
        ) : (
          <>
            {t("workIdHint.graph.p1")} <code style={{ color: "rgba(129,140,248,0.95)" }}>work_id</code>. {t("workIdHint.graph.p2")}
          </>
        )}
      </Typography>
    </Box>
  );
}
