import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { getLlmProviderPreset, isProbableOllamaBaseUrl } from "./llmProviderPresets.js";

/** @typedef {import("./llmProviderPresets.js").LlmProviderPresetId} LlmProviderPresetId */

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   cardSx: object,
 *   taskBaseUrls: {
 *     extraction: string,
 *     chat: string,
 *     vision: string,
 *     embeddings: string,
 *   },
 *   onApplyPreset: (values: import("./llmProviderPresets.js").LlmPresetFormValues) => void,
 * }} props
 */
export default function LlmProviderPresetsCard({ tk, cardSx, taskBaseUrls, onApplyPreset }) {
  const { t } = useI18n();
  const showOllamaHint = Object.values(taskBaseUrls || {}).some((url) => isProbableOllamaBaseUrl(url));

  /** @param {LlmProviderPresetId} id */
  function apply(id) {
    onApplyPreset(getLlmProviderPreset(id));
  }

  return (
    <Box sx={{ ...cardSx, padding: 2 }}>
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>
        {t("llm.presets.title")}
      </Typography>
      <Typography sx={{ marginTop: 0.5, fontSize: "0.72rem", color: tk.text.muted, lineHeight: 1.5 }}>
        {t("llm.presets.intro")}
      </Typography>
      <Box sx={{ marginTop: 1.5, display: "flex", flexWrap: "wrap", gap: 1 }}>
        <CursorSmallButton type="button" onClick={() => apply("openrouter")}>
          {t("llm.presets.openrouter")}
        </CursorSmallButton>
        <CursorSmallButton type="button" onClick={() => apply("vllm")}>
          {t("llm.presets.vllm")}
        </CursorSmallButton>
        <CursorSmallButton type="button" onClick={() => apply("ollama")}>
          {t("llm.presets.ollama")}
        </CursorSmallButton>
      </Box>
      {showOllamaHint ? (
        <Typography sx={{ marginTop: 1.25, fontSize: "0.72rem", color: tk.text.muted, lineHeight: 1.5 }}>
          {t("llm.presets.ollamaActiveHint")}
        </Typography>
      ) : null}
    </Box>
  );
}
