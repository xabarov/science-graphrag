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
  const metrics = stage?.metrics && typeof stage.metrics === "object" ? stage.metrics : {};
  const detail =
    (stage?.detail_message && String(stage.detail_message).trim()) ||
    (metrics.detail_message && String(metrics.detail_message).trim()) ||
    "";
  const subCur = Number(stage?.subprogress_current ?? metrics.subprogress_current);
  const subTot = Number(stage?.subprogress_total ?? metrics.subprogress_total);
  const subStr =
    Number.isFinite(subCur) && Number.isFinite(subTot) && subTot > 0 ? `${Math.round(subCur)}/${Math.round(subTot)}` : "";
  const etaMs = stage?.expected_duration_ms;
  const eta =
    typeof etaMs === "number" && Number.isFinite(etaMs) && etaMs > 0
      ? t("workspace.ingest.stageEtaSeconds", { sec: String(Math.max(1, Math.round(etaMs / 1000))) })
      : null;

  return (
    <Box sx={{ py: 0.15 }}>
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
        {subStr ? (
          <Typography sx={{ fontSize: "0.65rem", color: "rgba(129,140,248,0.75)" }}>{subStr}</Typography>
        ) : null}
        {eta ? (
          <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.38)" }}>{eta}</Typography>
        ) : null}
      </Box>
      {detail ? (
        <Typography sx={{ fontSize: "0.62rem", color: "rgba(255,255,255,0.35)", pl: 0.5, mt: -0.1 }} noWrap>
          {detail.slice(0, 120)}
        </Typography>
      ) : null}
    </Box>
  );
}
