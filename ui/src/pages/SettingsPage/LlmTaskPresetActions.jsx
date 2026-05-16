import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { listTaskPresetActions } from "./llmProviderPresets.js";

/** @typedef {import("./llmProviderPresets.js").LlmTaskId} LlmTaskId */
/** @typedef {import("./llmProviderPresets.js").LlmPresetFormPatch} LlmPresetFormPatch */

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   task: LlmTaskId,
 *   onApply: (patch: LlmPresetFormPatch) => void,
 * }} props
 */
export default function LlmTaskPresetActions({ tk, task, onApply }) {
  const { t } = useI18n();
  const actions = listTaskPresetActions(task);

  return (
    <Box sx={{ marginBottom: 0.5 }}>
      <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, marginBottom: 0.75 }}>
        {t("llm.presets.taskQuickFill")}
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
        {actions.map((action) => (
          <CursorSmallButton key={action.id} type="button" onClick={() => onApply(action.patch)}>
            {t(`llm.presets.task.${task}.${action.id}`)}
          </CursorSmallButton>
        ))}
      </Box>
    </Box>
  );
}
