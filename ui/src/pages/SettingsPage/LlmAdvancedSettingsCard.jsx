import React from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import FormControl from "@mui/material/FormControl";
import FormHelperText from "@mui/material/FormHelperText";
import InputAdornment from "@mui/material/InputAdornment";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { LLM_ADVANCED_GROUPS } from "./llmRuntimeOverrideKeys.js";
import { advancedFieldLabel } from "./llmSettingsMeta.js";

const AGENT_RUNTIME_SLUGS = ["langgraph_research_v1", "langgraph_supervisor_v1", "retrieval_v1"];

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   fieldSx: object,
 *   cardSx: object,
 *   llm: object,
 *   llmSchemaFields: Array<{ id: string, description?: string }>,
 *   advValues: Record<string, string>,
 *   setAdvField: (key: string, value: string) => void,
 *   keysByGroup: Record<string, string[]>,
 *   advancedOpen: boolean,
 *   setAdvancedOpen: (v: boolean) => void,
 *   restoreRecommendedDefaults: () => void,
 * }} props
 */
export default function LlmAdvancedSettingsCard({
  tk,
  fieldSx,
  cardSx,
  llm,
  llmSchemaFields,
  advValues,
  setAdvField,
  keysByGroup,
  advancedOpen,
  setAdvancedOpen,
  restoreRecommendedDefaults,
}) {
  const { t } = useI18n();

  function fieldLabel(key) {
    return advancedFieldLabel(t, key);
  }

  function fieldHelper(key) {
    const row = llmSchemaFields.find((f) => f.id === key);
    return row?.description || "";
  }

  function renderAdvancedField(key) {
    if (key === "agent_runtime") {
      return (
        <FormControl key={key} size="small" fullWidth sx={{ minWidth: 0 }}>
          <InputLabel id={`adv-${key}`}>{fieldLabel(key)}</InputLabel>
          <Select
            labelId={`adv-${key}`}
            label={fieldLabel(key)}
            value={advValues[key] ?? ""}
            onChange={(e) => setAdvField(key, e.target.value)}
          >
            {AGENT_RUNTIME_SLUGS.map((slug) => (
              <MenuItem key={slug} value={slug}>
                {slug}
              </MenuItem>
            ))}
          </Select>
          {fieldHelper(key) ? <FormHelperText sx={{ color: tk.text.muted }}>{fieldHelper(key)}</FormHelperText> : null}
        </FormControl>
      );
    }
    if (key === "agent_turn_policy_llm_enabled" || key === "llm_distributed_quota_enabled") {
      return (
        <Box key={key} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Switch
            checked={advValues[key] === "1" || advValues[key] === "true"}
            onChange={(e) => setAdvField(key, e.target.checked ? "1" : "0")}
          />
          <Box sx={{ flex: 1 }}>
            <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary }}>{fieldLabel(key)}</Typography>
            {fieldHelper(key) ? (
              <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, marginTop: 0.25 }}>{fieldHelper(key)}</Typography>
            ) : null}
          </Box>
        </Box>
      );
    }
    const cell = llm?.advanced_controls?.[key];
    const effHint =
      cell && cell.persisted != null && String(cell.persisted) !== String(cell.effective)
        ? t("llm.advanced.effectiveHint", { value: cell.effective })
        : null;
    if (key === "llm_distributed_quota_key_prefix") {
      return (
        <TextField
          key={key}
          label={fieldLabel(key)}
          size="small"
          value={advValues[key] ?? ""}
          onChange={(e) => setAdvField(key, e.target.value)}
          sx={fieldSx}
          fullWidth
          helperText={fieldHelper(key)}
        />
      );
    }
    const isFloat =
      key === "agent_step_timeout_seconds" ||
      key === "agent_turn_policy_classifier_timeout_seconds" ||
      key === "work_dedup_llm_timeout_s" ||
      key === "author_dedup_llm_timeout_s" ||
      key === "llm_distributed_quota_acquire_timeout_seconds";
    return (
      <TextField
        key={key}
        label={fieldLabel(key)}
        size="small"
        type="number"
        value={advValues[key] ?? ""}
        onChange={(e) => setAdvField(key, e.target.value)}
        sx={fieldSx}
        fullWidth
        inputProps={isFloat ? { step: 0.5 } : { step: 1 }}
        helperText={effHint ? `${fieldHelper(key) ? `${fieldHelper(key)} · ` : ""}${effHint}` : fieldHelper(key)}
        InputProps={
          isFloat
            ? {
                endAdornment: <InputAdornment position="end">{t("llm.field.secondsSuffix")}</InputAdornment>,
              }
            : undefined
        }
      />
    );
  }

  function renderAdvancedGroup(groupId, titleKey) {
    const keys = keysByGroup[groupId] || [];
    if (!keys.length) return null;
    return (
      <Box key={groupId} sx={{ marginTop: 2 }}>
        <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: tk.text.secondary, marginBottom: 1 }}>
          {t(titleKey)}
        </Typography>
        {groupId === "llm_distributed_quota" ? (
          <Typography sx={{ marginBottom: 1, fontSize: "0.72rem", color: tk.text.muted, lineHeight: 1.5 }}>
            {t("llm.advanced.distributedQuota.operatorBlurb")}
          </Typography>
        ) : null}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
            gap: 1.5,
          }}
        >
          {keys.map((k) => renderAdvancedField(k))}
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ ...cardSx, padding: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, flexWrap: "wrap" }}>
        <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>{t("llm.advanced.title")}</Typography>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Switch checked={advancedOpen} onChange={(e) => setAdvancedOpen(e.target.checked)} />
          <Typography sx={{ fontSize: "0.8125rem", color: tk.text.secondary }}>{t("llm.advanced.toggle")}</Typography>
        </Box>
      </Box>
      <Typography sx={{ marginTop: 0.75, fontSize: "0.72rem", color: tk.text.muted, lineHeight: 1.5 }}>{t("llm.advanced.intro")}</Typography>
      <Collapse in={advancedOpen}>
        <Box sx={{ marginTop: 1.5, display: "flex", gap: 1, flexWrap: "wrap" }}>
          <CursorSmallButton type="button" onClick={restoreRecommendedDefaults}>
            {t("llm.advanced.restoreRecommended")}
          </CursorSmallButton>
        </Box>
        {renderAdvancedGroup("llm_concurrency", LLM_ADVANCED_GROUPS.llm_concurrency)}
        {renderAdvancedGroup("llm_distributed_quota", LLM_ADVANCED_GROUPS.llm_distributed_quota)}
        {renderAdvancedGroup("llm_deadlines", LLM_ADVANCED_GROUPS.llm_deadlines)}
        {renderAdvancedGroup("llm_agent_runtime", LLM_ADVANCED_GROUPS.llm_agent_runtime)}
        {renderAdvancedGroup("llm_advanced", "llm.advanced.group.other")}
      </Collapse>
    </Box>
  );
}
