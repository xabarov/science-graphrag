import React from "react";
import Box from "@mui/material/Box";
import InputAdornment from "@mui/material/InputAdornment";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../i18n/useI18n.js";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   cardSx: object,
 *   fieldSx: object,
 *   baseUrl: string,
 *   setBaseUrl: (v: string) => void,
 *   model: string,
 *   setModel: (v: string) => void,
 *   vlModel: string,
 *   setVlModel: (v: string) => void,
 *   vlBaseUrl: string,
 *   setVlBaseUrl: (v: string) => void,
 *   temperature: string,
 *   setTemperature: (v: string) => void,
 *   timeoutSeconds: string,
 *   setTimeoutSeconds: (v: string) => void,
 *   providerSummaryLine: string,
 * }} props
 */
export default function LlmProviderSettingsCard({
  tk,
  cardSx,
  fieldSx,
  baseUrl,
  setBaseUrl,
  model,
  setModel,
  vlModel,
  setVlModel,
  vlBaseUrl,
  setVlBaseUrl,
  temperature,
  setTemperature,
  timeoutSeconds,
  setTimeoutSeconds,
  providerSummaryLine,
}) {
  const { t } = useI18n();
  return (
    <Box
      sx={{
        ...cardSx,
        padding: 2,
      }}
    >
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>{t("llm.panel.title")}</Typography>
      <Typography sx={{ marginTop: 0.75, fontSize: "0.75rem", color: tk.text.secondary, lineHeight: 1.5 }}>
        {providerSummaryLine}
      </Typography>

      <Box
        sx={{
          marginTop: 2,
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
          gap: 1.5,
        }}
      >
        <TextField
          label={t("llm.field.baseUrl")}
          size="small"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          sx={fieldSx}
          fullWidth
        />
        <TextField label={t("llm.field.model")} size="small" value={model} onChange={(e) => setModel(e.target.value)} sx={fieldSx} fullWidth />
        <TextField label={t("llm.field.vlModel")} size="small" value={vlModel} onChange={(e) => setVlModel(e.target.value)} sx={fieldSx} fullWidth />
        <TextField
          label={t("llm.field.vlBaseUrl")}
          size="small"
          value={vlBaseUrl}
          onChange={(e) => setVlBaseUrl(e.target.value)}
          sx={fieldSx}
          fullWidth
          helperText={t("llm.hint.vlBaseUrlFallback")}
        />
        <TextField
          label={t("llm.field.temperature")}
          size="small"
          type="number"
          value={temperature}
          onChange={(e) => setTemperature(e.target.value)}
          sx={fieldSx}
          fullWidth
        />
        <TextField
          label={t("llm.field.timeout")}
          size="small"
          type="number"
          value={timeoutSeconds}
          onChange={(e) => setTimeoutSeconds(e.target.value)}
          sx={fieldSx}
          fullWidth
          helperText={t("llm.hint.transportTimeout")}
          InputProps={{
            endAdornment: <InputAdornment position="end">{t("llm.field.secondsSuffix")}</InputAdornment>,
          }}
        />
      </Box>
    </Box>
  );
}
