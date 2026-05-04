import React from "react";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Typography from "@mui/material/Typography";

import { formatMetricValue } from "./chatThreadMetrics.js";

export default function ChatThreadMetadataDialog({ open, onClose, tk, t, meta, maxMetaBar }) {
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
      <DialogTitle sx={{ fontSize: "0.9rem", color: tk.text.primary }}>{t("chat.thread.meta.title")}</DialogTitle>
      <DialogContent sx={{ pt: "8px !important" }}>
        <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
          {[
            { label: t("chat.thread.meta.durationMs"), value: formatMetricValue(meta.durationMs, { unit: " ms" }), bar: meta.durationMs },
            { label: t("chat.thread.meta.totalTokens"), value: formatMetricValue(meta.totalTokens), bar: meta.totalTokens },
            {
              label: t("chat.thread.meta.tokensPerSecond"),
              value: formatMetricValue(meta.tokensPerSecond, { digits: 1 }),
              bar: meta.tokensPerSecond,
            },
            { label: t("chat.thread.meta.costUsd"), value: formatMetricValue(meta.costUsd, { digits: 5 }), bar: meta.costUsd },
          ].map((row) => (
            <Box key={row.label} sx={{ p: 1, border: `1px solid ${tk.border.default}`, borderRadius: "6px", backgroundColor: tk.control.outlinedBg }}>
              <Typography sx={{ fontSize: "0.69rem", color: tk.text.secondary }}>{row.label}</Typography>
              <Typography sx={{ fontSize: "0.86rem", color: tk.text.primary, fontWeight: 600 }}>{row.value}</Typography>
              <Box sx={{ mt: 0.6, height: 4, borderRadius: 6, backgroundColor: tk.border.default, overflow: "hidden" }}>
                <Box
                  sx={{
                    width: `${Math.min(100, Math.max(0, (((row.bar ?? 0) / maxMetaBar) * 100))) || 0}%`,
                    height: "100%",
                    backgroundColor: "rgba(99,102,241,0.65)",
                  }}
                />
              </Box>
            </Box>
          ))}
        </Box>
        <Box sx={{ mt: 1, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0.5 }}>
          <Typography sx={{ fontSize: "0.76rem", color: tk.text.secondary }}>
            {t("chat.thread.meta.promptTokens")}: {formatMetricValue(meta.promptTokens)}
          </Typography>
          <Typography sx={{ fontSize: "0.76rem", color: tk.text.secondary }}>
            {t("chat.thread.meta.completionTokens")}: {formatMetricValue(meta.completionTokens)}
          </Typography>
          <Typography sx={{ fontSize: "0.76rem", color: tk.text.secondary }}>
            {t("chat.thread.meta.events")}: {formatMetricValue(meta.eventsCount)}
          </Typography>
          <Typography sx={{ fontSize: "0.76rem", color: tk.text.secondary }}>
            {t("chat.thread.meta.citations")}: {formatMetricValue(meta.citationCount)}
          </Typography>
        </Box>
        <Typography sx={{ mt: 0.8, fontSize: "0.76rem", color: tk.text.secondary }}>
          {t("chat.thread.meta.answerClass")}: {meta.answerClass || "—"}
        </Typography>
      </DialogContent>
    </Dialog>
  );
}
