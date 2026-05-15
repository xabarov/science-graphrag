import React from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../i18n/useI18n.js";

function SourceChip({ tk, label }) {
  if (!label) return null;
  return (
    <Chip
      label={label}
      size="small"
      sx={{
        height: 20,
        fontSize: "0.6875rem",
        marginTop: 0.75,
        backgroundColor: tk.control.chipMutedBg,
        color: tk.control.chipMutedFg,
        border: `1px solid ${tk.border.default}`,
      }}
    />
  );
}

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   cardSx: object,
 *   fieldSx: object,
 *   llm: object,
 *   model: string,
 *   setModel: (v: string) => void,
 *   chatModel: string,
 *   setChatModel: (v: string) => void,
 *   vlModel: string,
 *   setVlModel: (v: string) => void,
 *   vlBaseUrl: string,
 *   setVlBaseUrl: (v: string) => void,
 * }} props
 */
export default function LlmTaskOverridesCard({
  tk,
  cardSx,
  fieldSx,
  llm,
  model,
  setModel,
  chatModel,
  setChatModel,
  vlModel,
  setVlModel,
  vlBaseUrl,
  setVlBaseUrl,
}) {
  const { t } = useI18n();
  const tasks = llm?.tasks || {};
  const emb = tasks.embeddings || {};
  const resolvedVlModel = (llm?.effective?.resolved_vl_model || "").trim();
  const resolvedVlBaseUrl = (llm?.effective?.resolved_vl_base_url || "").trim();

  function keySourceLabel(source) {
    if (source === "server_managed") return t("llm.keySource.serverManaged");
    if (source === "environment") return t("llm.keySource.environment");
    if (source === "inherited") return t("llm.keySource.inherited");
    return t("llm.keySource.none");
  }

  return (
    <Box
      sx={{
        ...cardSx,
        padding: 2,
      }}
    >
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>
        {t("llm.tasks.title")}
      </Typography>
      <Typography sx={{ marginTop: 0.5, fontSize: "0.72rem", color: tk.text.muted, lineHeight: 1.5 }}>
        {t("llm.tasks.intro")}
      </Typography>

      <Box sx={{ marginTop: 2, display: "flex", flexDirection: "column", gap: 2 }}>
        <Box>
          <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: tk.text.secondary }}>
            {t("llm.tasks.extraction")}
          </Typography>
          <TextField
            label={t("llm.field.model")}
            size="small"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            sx={{ ...fieldSx, marginTop: 1 }}
            fullWidth
          />
          <SourceChip tk={tk} label={keySourceLabel(tasks.extraction?.api_key?.source)} />
        </Box>

        <Box>
          <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: tk.text.secondary }}>
            {t("llm.tasks.chat")}
          </Typography>
          <TextField
            label={t("llm.field.chatModel")}
            size="small"
            value={chatModel}
            onChange={(e) => setChatModel(e.target.value)}
            sx={{ ...fieldSx, marginTop: 1 }}
            fullWidth
            helperText={t("llm.hint.chatModelFallback")}
          />
          {tasks.chat?.inherits_extraction_model ? (
            <Typography sx={{ marginTop: 0.5, fontSize: "0.6875rem", color: tk.text.muted }}>
              {t("llm.tasks.inheritsExtractionModel")}
            </Typography>
          ) : null}
          <SourceChip tk={tk} label={keySourceLabel(tasks.chat?.api_key?.source)} />
        </Box>

        <Box>
          <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: tk.text.secondary }}>
            {t("llm.tasks.vision")}
          </Typography>
          <Box
            sx={{
              marginTop: 1,
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
              gap: 1.5,
            }}
          >
            <TextField
              label={t("llm.field.vlModel")}
              size="small"
              value={vlModel}
              onChange={(e) => setVlModel(e.target.value)}
              sx={fieldSx}
              fullWidth
              placeholder={!vlModel.trim() && resolvedVlModel ? resolvedVlModel : undefined}
            />
            <TextField
              label={t("llm.field.vlBaseUrl")}
              size="small"
              value={vlBaseUrl}
              onChange={(e) => setVlBaseUrl(e.target.value)}
              sx={fieldSx}
              fullWidth
              helperText={t("llm.hint.vlBaseUrlFallback")}
              placeholder={!vlBaseUrl.trim() && resolvedVlBaseUrl ? resolvedVlBaseUrl : undefined}
            />
          </Box>
          <SourceChip tk={tk} label={keySourceLabel(tasks.vision?.api_key?.source)} />
        </Box>

        <Box
          sx={{
            borderTop: `1px solid ${tk.border.default}`,
            paddingTop: 2,
          }}
        >
          <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: tk.text.secondary }}>
            {t("llm.tasks.embeddings")}
          </Typography>
          <Typography sx={{ marginTop: 0.75, fontSize: "0.8125rem", color: tk.text.primary }}>
            {t("llm.tasks.embeddingsMode", { mode: emb.mode || "—", label: emb.model_label || "—" })}
          </Typography>
          {emb.mode === "openrouter" ? (
            <Typography sx={{ marginTop: 0.5, fontSize: "0.72rem", color: tk.text.muted, lineHeight: 1.5 }}>
              {t("llm.tasks.embeddingsKeyHint")}
            </Typography>
          ) : null}
        </Box>
      </Box>
    </Box>
  );
}
