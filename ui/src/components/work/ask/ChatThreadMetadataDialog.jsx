import React from "react";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Typography from "@mui/material/Typography";

import { formatMetricValue } from "./chatThreadMetrics.js";

export default function ChatThreadMetadataDialog({ open, onClose, tk, t, meta }) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      slotProps={{
        paper: {
          sx: {
            backgroundColor: tk.surface.panel,
            border: `1px solid ${tk.border.default}`,
            borderRadius: "6px",
            minWidth: { xs: 300, sm: 420 },
          },
        },
      }}
    >
      <DialogTitle sx={{ fontSize: "0.9rem", color: tk.text.primary, pb: 0 }}>
        <Box component="div">{t("chat.thread.meta.title")}</Box>
        <Typography component="div" sx={{ mt: 0.35, fontSize: "0.72rem", fontWeight: 400, color: tk.text.muted, lineHeight: 1.35 }}>
          {t("chat.thread.meta.subtitle")}
        </Typography>
      </DialogTitle>
      <DialogContent sx={{ pt: "10px !important" }}>
        <Typography sx={{ fontSize: "0.7rem", fontWeight: 600, color: tk.text.muted, mb: 0.75, letterSpacing: "0.02em" }}>
          {t("chat.thread.meta.sectionPerformance")}
        </Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, mb: 1.5 }}>
          <Box sx={{ p: 1, border: `1px solid ${tk.border.default}`, borderRadius: "6px", backgroundColor: tk.control.outlinedBg }}>
            <Typography sx={{ fontSize: "0.69rem", color: tk.text.secondary }}>{t("chat.thread.meta.tokensPerSecond")}</Typography>
            <Typography sx={{ fontSize: "0.86rem", color: tk.text.primary, fontWeight: 600 }}>
              {formatMetricValue(meta.tokensPerSecond, { digits: 1 })}
            </Typography>
          </Box>
          <Box sx={{ p: 1, border: `1px solid ${tk.border.default}`, borderRadius: "6px", backgroundColor: tk.control.outlinedBg }}>
            <Typography sx={{ fontSize: "0.69rem", color: tk.text.secondary }}>{t("chat.thread.meta.durationMs")}</Typography>
            <Typography sx={{ fontSize: "0.86rem", color: tk.text.primary, fontWeight: 600 }}>
              {formatMetricValue(meta.durationMs, { unit: " ms" })}
            </Typography>
          </Box>
        </Box>

        <Typography sx={{ fontSize: "0.7rem", fontWeight: 600, color: tk.text.muted, mb: 0.75, letterSpacing: "0.02em" }}>
          {t("chat.thread.meta.sectionTokens")}
        </Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0.5, mb: 1.5 }}>
          <Typography sx={{ fontSize: "0.76rem", color: tk.text.secondary }}>
            {t("chat.thread.meta.promptTokens")}: {formatMetricValue(meta.promptTokens)}
          </Typography>
          <Typography sx={{ fontSize: "0.76rem", color: tk.text.secondary }}>
            {t("chat.thread.meta.completionTokens")}: {formatMetricValue(meta.completionTokens)}
          </Typography>
          <Typography sx={{ fontSize: "0.76rem", color: tk.text.secondary, gridColumn: "1 / -1" }}>
            {t("chat.thread.meta.totalTokens")}: {formatMetricValue(meta.totalTokens)}
          </Typography>
        </Box>

        <Typography sx={{ fontSize: "0.7rem", fontWeight: 600, color: tk.text.muted, mb: 0.75, letterSpacing: "0.02em" }}>
          {t("chat.thread.meta.sectionCostModel")}
        </Typography>
        <Box sx={{ p: 1, border: `1px solid ${tk.border.default}`, borderRadius: "6px", backgroundColor: tk.control.outlinedBg, mb: 1 }}>
          <Typography sx={{ fontSize: "0.69rem", color: tk.text.secondary }}>{t("chat.thread.meta.costUsd")}</Typography>
          <Typography sx={{ fontSize: "0.86rem", color: tk.text.primary, fontWeight: 600 }}>
            {formatMetricValue(meta.costUsd, { digits: 5 })}
          </Typography>
          {meta.costUsdIsEstimated ? (
            <Typography sx={{ fontSize: "0.65rem", color: tk.text.muted, mt: 0.35, lineHeight: 1.35 }}>
              {t("chat.thread.meta.costUsdEstimatedHint")}
            </Typography>
          ) : null}
        </Box>
        {meta.openrouterChatRefPricing ? (
          <Typography sx={{ fontSize: "0.74rem", color: tk.text.muted, lineHeight: 1.4, fontFamily: "monospace", wordBreak: "break-all" }}>
            {t("chat.thread.meta.modelChat", { model: meta.openrouterChatRefPricing.model })}
          </Typography>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
