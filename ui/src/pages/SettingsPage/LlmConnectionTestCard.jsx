import React, { useMemo } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { settingsAlertMutedSx, settingsCardSx } from "../../theme/settingsFormSx.js";

function toneForResult(result) {
  if (!result) return "info";
  if (result.status === "connected") return "success";
  if (result.status === "unexpected_response") return "warning";
  return "error";
}

export default function LlmConnectionTestCard({
  disabled,
  testing,
  result,
  onTestSaved,
  onTestDraft,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const cardSx = useMemo(() => settingsCardSx(tk), [tk]);
  const alertMutedSx = useMemo(() => settingsAlertMutedSx(tk), [tk]);
  const tone = toneForResult(result);

  const statusTitle =
    result?.status === "connected"
      ? t("llm.test.connected")
      : result?.status === "unexpected_response"
        ? t("llm.test.unexpected")
        : result?.error_kind || t("llm.test.connectionError");

  const tasksSummary = Array.isArray(result?.tasks) ? result.tasks : null;
  const taskLabelById = {
    extraction: t("llm.card.extraction"),
    chat: t("llm.card.chat"),
    vision: t("llm.card.vision"),
    embeddings: t("llm.card.embeddings"),
  };

  return (
    <Box
      sx={{
        ...cardSx,
        padding: 2,
      }}
    >
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>{t("llm.test.title")}</Typography>
      <Typography sx={{ marginTop: 0.75, fontSize: "0.75rem", color: tk.text.secondary, lineHeight: 1.5 }}>
        {t("llm.test.blurb")}
      </Typography>

      <Box sx={{ display: "flex", gap: 1, marginTop: 2, flexWrap: "wrap" }}>
        <CursorButton onClick={onTestSaved} disabled={disabled || testing}>
          {testing ? t("llm.test.testing") : t("llm.test.saved")}
        </CursorButton>
        <CursorButton onClick={onTestDraft} disabled={disabled || testing}>
          {testing ? t("llm.test.testing") : t("llm.test.draft")}
        </CursorButton>
      </Box>

      {result ? (
        <Alert
          severity={tone}
          sx={{
            marginTop: 2,
            ...alertMutedSx,
          }}
        >
          <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600 }}>{statusTitle}</Typography>
          <Typography sx={{ fontSize: "0.75rem", marginTop: 0.5, color: tk.text.primary }}>{result.message}</Typography>
          <Typography sx={{ fontSize: "0.75rem", marginTop: 1, color: tk.text.secondary }}>
            {[
              result.resolved?.base_url ? t("llm.test.baseUrl", { url: result.resolved.base_url }) : null,
              result.resolved?.model ? t("llm.test.model", { model: result.resolved.model }) : null,
              result.latency_ms != null ? t("llm.test.latency", { ms: result.latency_ms }) : null,
              result.tested_at ? t("llm.test.testedAt", { at: result.tested_at }) : null,
            ]
              .filter(Boolean)
              .join(" | ")}
          </Typography>
          {tasksSummary?.length ? (
            <Box sx={{ marginTop: 1.25 }}>
              {tasksSummary.map((taskResult) => {
                const ok = taskResult.status === "connected";
                const label = taskLabelById[taskResult.task] || taskResult.task;
                const statusText = t(ok ? "llm.test.taskOk" : "llm.test.taskError");
                return (
                  <Typography
                    key={taskResult.task}
                    sx={{ fontSize: "0.75rem", color: ok ? tk.state.successFg : tk.state.dangerFg }}
                  >
                    {`${statusText} · ${label}: ${taskResult.message || taskResult.error_kind || "-"}`}
                  </Typography>
                );
              })}
            </Box>
          ) : null}
        </Alert>
      ) : null}
    </Box>
  );
}
