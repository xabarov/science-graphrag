import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../i18n/useI18n.js";

/**
 * @param {{
 *   stage: { stage?: string, status?: string, message?: string, expected_duration_ms?: number | null },
 *   active: boolean,
 * }} props
 */
export default function IngestStageRow({ stage, active }) {
  const { t } = useI18n();
  const name = String(stage?.stage || stage?.name || "").trim() || t("workspace.ingest.stageUnknown");
  const status = String(stage?.status || "").toLowerCase();
  const etaMs = stage?.expected_duration_ms;
  const eta =
    typeof etaMs === "number" && Number.isFinite(etaMs) && etaMs > 0
      ? t("workspace.ingest.stageEtaSeconds", { sec: String(Math.max(1, Math.round(etaMs / 1000))) })
      : null;

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        py: 0.35,
        px: 0.5,
        borderRadius: "4px",
        backgroundColor: active ? "rgba(99,102,241,0.12)" : "transparent",
        border: active ? "1px solid rgba(129,140,248,0.35)" : "1px solid transparent",
      }}
    >
      <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.85)", flex: 1, fontFamily: "monospace" }}>
        {name}
      </Typography>
      <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.45)", textTransform: "uppercase" }}>
        {status || "—"}
      </Typography>
      {eta ? (
        <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.38)" }}>{eta}</Typography>
      ) : null}
    </Box>
  );
}
