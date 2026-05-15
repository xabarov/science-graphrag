import React from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

/**
 * Title row: inspector label + case/run/family/status chips.
 *
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   title: string,
 *   caseId: string | null,
 *   mode: "run" | "fixture",
 *   family: string,
 *   caseDetail: Record<string, unknown>,
 * }} props
 */
export default function BenchmarkCaseInspectorHeader({ tk, title, caseId, mode, family, caseDetail }) {
  const runCfg = /** @type {Record<string, unknown>} */ (caseDetail?.run_config || {});

  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap: 1,
        alignItems: "center",
        borderBottom: `1px solid ${tk.border.default}`,
        pb: 1.5,
      }}
    >
      <Typography sx={{ fontWeight: 700, fontSize: "0.9375rem" }}>{title}</Typography>
      <Chip size="small" label={`case: ${caseId || "-"}`} variant="outlined" />
      {mode === "run" && caseDetail.run_id ? (
        <Chip size="small" label={`run: ${String(caseDetail.run_id).slice(0, 8)}…`} variant="outlined" />
      ) : null}
      <Chip size="small" label={`family: ${family}`} variant="outlined" />
      {caseDetail.status != null ? (
        <Chip size="small" label={`status: ${String(caseDetail.status)}`} variant="outlined" />
      ) : null}
      {runCfg.model_profile ? (
        <Chip size="small" label={String(runCfg.model_profile)} variant="outlined" sx={{ maxWidth: 220 }} />
      ) : null}
      {runCfg.gold_source ? <Chip size="small" label={String(runCfg.gold_source)} variant="outlined" /> : null}
    </Box>
  );
}
