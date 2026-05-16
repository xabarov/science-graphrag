import React, { useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorPrimaryButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { outlinedAppTextFieldSx, settingsAlertMutedSx, settingsCardSx } from "../../theme/settingsFormSx.js";
import LlmAdvancedSettingsCard from "./LlmAdvancedSettingsCard.jsx";
import LlmConnectionTestCard from "./LlmConnectionTestCard.jsx";
import LlmSecretTextField from "./LlmSecretTextField.jsx";
import LlmProviderPresetsCard from "./LlmProviderPresetsCard.jsx";
import LlmTaskCard from "./LlmTaskCard.jsx";
import LlmTaskPresetActions from "./LlmTaskPresetActions.jsx";
import { computeSaveBlockingMessage } from "./llmSaveValidation.js";
import { buildAdvValuesFromLlm, buildLlmSettingsSubmitPayload } from "./llmSettingsPayload.js";
import { LLM_RUNTIME_OVERRIDE_KEYS, schemaGroupForKey } from "./llmRuntimeOverrideKeys.js";

function valueFromTask(tasks, role, key, fallback = "") {
  const taskValue = tasks?.[role]?.[key];
  if (taskValue !== undefined && taskValue !== null && taskValue !== "") {
    return taskValue;
  }
  return fallback;
}

function stringValue(value, fallback = "") {
  return String(value ?? fallback ?? "");
}

function embeddingsBaseUrlValue(llm, tasks) {
  return stringValue(
    valueFromTask(
      tasks,
      "embeddings",
      "base_url",
      llm?.effective?.resolved_embeddings_base_url || llm?.base_url || "",
    ),
  ).trim();
}

function embeddingsModelValue(llm, tasks) {
  return stringValue(
    valueFromTask(
      tasks,
      "embeddings",
      "model",
      tasks?.embeddings?.model_label || llm?.embeddings_model || "",
    ),
  ).trim();
}

export default function LlmSettingsPanel({
  llm,
  schema,
  saving,
  testing,
  saveError,
  testResult,
  onSave,
  onTestSaved,
  onTestDraft,
  onDirtyChange,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const fieldSx = useMemo(() => outlinedAppTextFieldSx(tk), [tk]);
  const cardSx = useMemo(() => settingsCardSx(tk), [tk]);
  const alertMutedSx = useMemo(() => settingsAlertMutedSx(tk), [tk]);

  const [baseUrl, setBaseUrl] = useState(llm?.base_url || "");
  const [model, setModel] = useState(llm?.model || "");
  const [chatModel, setChatModel] = useState(llm?.chat_model || "");
  const [chatBaseUrl, setChatBaseUrl] = useState(llm?.chat_base_url || "");
  const [chatTemperature, setChatTemperature] = useState(
    String(llm?.tasks?.chat?.temperature ?? llm?.temperature ?? 0),
  );
  const [chatTimeoutSeconds, setChatTimeoutSeconds] = useState(
    String(llm?.tasks?.chat?.timeout_seconds ?? llm?.effective?.resolved_timeout_seconds ?? 180),
  );
  const [vlModel, setVlModel] = useState("");
  const [vlBaseUrl, setVlBaseUrl] = useState("");
  const [vlTemperature, setVlTemperature] = useState(String(llm?.tasks?.vision?.temperature ?? 0));
  const [vlTimeoutSeconds, setVlTimeoutSeconds] = useState(String(llm?.tasks?.vision?.timeout_seconds ?? 300));
  const [temperature, setTemperature] = useState(String(llm?.temperature ?? 0));
  const [timeoutSeconds, setTimeoutSeconds] = useState(String(llm?.effective?.resolved_timeout_seconds ?? 180));
  const [apiKey, setApiKey] = useState("");
  const [visionApiKey, setVisionApiKey] = useState("");
  const [chatApiKey, setChatApiKey] = useState("");
  const [embeddingsBaseUrl, setEmbeddingsBaseUrl] = useState(
    embeddingsBaseUrlValue(llm, llm?.tasks || {}),
  );
  const [embeddingsModel, setEmbeddingsModel] = useState(
    embeddingsModelValue(llm, llm?.tasks || {}),
  );
  const [embeddingsTimeoutSeconds, setEmbeddingsTimeoutSeconds] = useState(
    String(llm?.tasks?.embeddings?.timeout_seconds ?? 60),
  );
  const [embeddingsApiKey, setEmbeddingsApiKey] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [advValues, setAdvValues] = useState(() => buildAdvValuesFromLlm(llm));

  const hasSavedSecret = Boolean(llm?.status?.has_saved_secret);
  const hasRevealableSecret = hasSavedSecret;
  const hasSavedVisionSecret = Boolean(llm?.status?.has_saved_vision_secret || hasRevealableSecret);
  const hasSavedChatSecret = Boolean(llm?.status?.has_saved_chat_secret || hasRevealableSecret);
  const hasSavedEmbeddingsSecret = Boolean(llm?.status?.has_saved_embeddings_secret || hasRevealableSecret);
  const tasks = llm?.tasks || {};

  const llmSchemaFields = useMemo(() => {
    const sec = schema?.sections?.find((s) => s.id === "llm");
    return sec?.fields || [];
  }, [schema]);

  const keysByGroup = useMemo(() => {
    const m = {
      llm_concurrency: [],
      llm_distributed_quota: [],
      llm_deadlines: [],
      llm_agent_runtime: [],
      llm_advanced: [],
    };
    for (const k of LLM_RUNTIME_OVERRIDE_KEYS) {
      const g = schemaGroupForKey(k, llmSchemaFields);
      const bucket = Object.prototype.hasOwnProperty.call(m, g) ? g : "llm_advanced";
      m[bucket].push(k);
    }
    return m;
  }, [llmSchemaFields]);

  React.useEffect(() => {
    if (!llm) return;
    setBaseUrl(llm.base_url || "");
    setModel(llm.model || "");
    const nextTasks = llm.tasks || {};
    setChatModel(stringValue(valueFromTask(nextTasks, "chat", "model", llm.chat_model)));
    setChatBaseUrl(stringValue(valueFromTask(nextTasks, "chat", "base_url", llm.chat_base_url)));
    setChatTemperature(stringValue(valueFromTask(nextTasks, "chat", "temperature", llm.temperature ?? 0)));
    setChatTimeoutSeconds(
      stringValue(valueFromTask(nextTasks, "chat", "timeout_seconds", llm.effective?.resolved_timeout_seconds ?? 180)),
    );
    setVlModel(stringValue(valueFromTask(nextTasks, "vision", "model", llm.vl_model)).trim());
    setVlBaseUrl(stringValue(valueFromTask(nextTasks, "vision", "base_url", llm.vl_base_url)).trim());
    setVlTemperature(stringValue(valueFromTask(nextTasks, "vision", "temperature", 0)));
    setVlTimeoutSeconds(stringValue(valueFromTask(nextTasks, "vision", "timeout_seconds", 300)));
    setTemperature(String(llm.temperature ?? 0));
    setTimeoutSeconds(String(llm.effective?.resolved_timeout_seconds ?? 180));
    setAdvValues(buildAdvValuesFromLlm(llm));
    setEmbeddingsBaseUrl(embeddingsBaseUrlValue(llm, nextTasks));
    setEmbeddingsModel(embeddingsModelValue(llm, nextTasks));
    setEmbeddingsTimeoutSeconds(stringValue(valueFromTask(nextTasks, "embeddings", "timeout_seconds", 60)));
  }, [llm]);

  const advDirty = useMemo(() => {
    const ac = llm?.advanced_controls;
    if (!ac) return false;
    for (const k of LLM_RUNTIME_OVERRIDE_KEYS) {
      const cell = ac[k];
      if (!cell) continue;
      const expected =
        k === "agent_turn_policy_llm_enabled" || k === "llm_distributed_quota_enabled"
          ? (cell.effective ? "1" : "0")
          : String(cell.effective);
      if ((advValues[k] ?? "") !== expected) return true;
    }
    return false;
  }, [llm, advValues]);

  const providerDirty = useMemo(() => {
    const currentTasks = llm?.tasks || {};
    return (
      baseUrl !== (llm?.base_url || "") ||
      model !== (llm?.model || "") ||
      chatModel.trim() !== stringValue(valueFromTask(currentTasks, "chat", "model", llm?.chat_model)).trim() ||
      chatBaseUrl.trim() !== stringValue(valueFromTask(currentTasks, "chat", "base_url", llm?.chat_base_url)).trim() ||
      Number(chatTemperature) !== Number(valueFromTask(currentTasks, "chat", "temperature", llm?.temperature ?? 0)) ||
      Number(chatTimeoutSeconds) !==
        Number(valueFromTask(currentTasks, "chat", "timeout_seconds", llm?.effective?.resolved_timeout_seconds ?? 180)) ||
      vlModel.trim() !== stringValue(valueFromTask(currentTasks, "vision", "model", llm?.vl_model)).trim() ||
      vlBaseUrl.trim() !== stringValue(valueFromTask(currentTasks, "vision", "base_url", llm?.vl_base_url)).trim() ||
      Number(vlTemperature) !== Number(valueFromTask(currentTasks, "vision", "temperature", 0)) ||
      Number(vlTimeoutSeconds) !== Number(valueFromTask(currentTasks, "vision", "timeout_seconds", 300)) ||
      Number(temperature) !== Number(llm?.temperature ?? 0) ||
      Number(timeoutSeconds) !== Number(llm?.effective?.resolved_timeout_seconds ?? 180) ||
      Boolean(apiKey.trim()) ||
      Boolean(chatApiKey.trim()) ||
      Boolean(visionApiKey.trim()) ||
      Boolean(embeddingsApiKey.trim()) ||
      embeddingsBaseUrl.trim() !== embeddingsBaseUrlValue(llm, currentTasks) ||
      embeddingsModel.trim() !== embeddingsModelValue(llm, currentTasks) ||
      Number(embeddingsTimeoutSeconds) !== Number(valueFromTask(currentTasks, "embeddings", "timeout_seconds", 60))
    );
  }, [
    apiKey,
    baseUrl,
    chatBaseUrl,
    chatApiKey,
    chatModel,
    chatTemperature,
    chatTimeoutSeconds,
    embeddingsApiKey,
    embeddingsBaseUrl,
    embeddingsModel,
    embeddingsTimeoutSeconds,
    llm,
    model,
    temperature,
    timeoutSeconds,
    vlBaseUrl,
    vlModel,
    vlTemperature,
    vlTimeoutSeconds,
    visionApiKey,
  ]);

  const dirty = providerDirty || advDirty;

  const advancedValidationMessage = computeSaveBlockingMessage(t, advValues, timeoutSeconds);

  React.useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);

  function setAdvField(key, value) {
    setAdvValues((prev) => ({ ...prev, [key]: value }));
  }

  function restoreRecommendedDefaults() {
    const rec = llm?.recommended_advanced || {};
    const next = {};
    for (const k of LLM_RUNTIME_OVERRIDE_KEYS) {
      if (rec[k] === undefined || rec[k] === null) continue;
      next[k] = k === "agent_turn_policy_llm_enabled" ? (rec[k] ? "1" : "0") : String(rec[k]);
    }
    setAdvValues((prev) => ({ ...prev, ...next }));
  }

  /** @param {import("./llmProviderPresets.js").LlmPresetFormPatch} patch */
  function applyPresetPatch(patch) {
    if (patch.baseUrl !== undefined) setBaseUrl(patch.baseUrl);
    if (patch.model !== undefined) setModel(patch.model);
    if (patch.temperature !== undefined) setTemperature(patch.temperature);
    if (patch.timeoutSeconds !== undefined) setTimeoutSeconds(patch.timeoutSeconds);
    if (patch.apiKey !== undefined) setApiKey(patch.apiKey);
    if (patch.chatModel !== undefined) setChatModel(patch.chatModel);
    if (patch.chatBaseUrl !== undefined) setChatBaseUrl(patch.chatBaseUrl);
    if (patch.chatTemperature !== undefined) setChatTemperature(patch.chatTemperature);
    if (patch.chatTimeoutSeconds !== undefined) setChatTimeoutSeconds(patch.chatTimeoutSeconds);
    if (patch.chatApiKey !== undefined) setChatApiKey(patch.chatApiKey);
    if (patch.vlModel !== undefined) setVlModel(patch.vlModel);
    if (patch.vlBaseUrl !== undefined) setVlBaseUrl(patch.vlBaseUrl);
    if (patch.vlTemperature !== undefined) setVlTemperature(patch.vlTemperature);
    if (patch.vlTimeoutSeconds !== undefined) setVlTimeoutSeconds(patch.vlTimeoutSeconds);
    if (patch.visionApiKey !== undefined) setVisionApiKey(patch.visionApiKey);
    if (patch.embeddingsBaseUrl !== undefined) setEmbeddingsBaseUrl(patch.embeddingsBaseUrl);
    if (patch.embeddingsModel !== undefined) setEmbeddingsModel(patch.embeddingsModel);
    if (patch.embeddingsTimeoutSeconds !== undefined) setEmbeddingsTimeoutSeconds(patch.embeddingsTimeoutSeconds);
    if (patch.embeddingsApiKey !== undefined) setEmbeddingsApiKey(patch.embeddingsApiKey);
  }

  /** @param {import("./llmProviderPresets.js").LlmPresetFormValues} values */
  function applyProviderPreset(values) {
    applyPresetPatch(values);
  }

  function submit() {
    if (advancedValidationMessage) return;
    const payload = buildLlmSettingsSubmitPayload({
      baseUrl,
      model,
      chatModel,
      chatBaseUrl,
      temperature: Number(temperature),
      timeoutSeconds: Number(timeoutSeconds),
      vlModel,
      vlBaseUrl,
      vlTemperature: Number(vlTemperature),
      vlTimeoutSeconds: Number(vlTimeoutSeconds),
      llm,
      apiKey,
      chatApiKey,
      visionApiKey,
      chatTemperature: Number(chatTemperature),
      chatTimeoutSeconds: Number(chatTimeoutSeconds),
      embeddingsBaseUrl,
      embeddingsModel,
      embeddingsTimeoutSeconds: Number(embeddingsTimeoutSeconds),
      embeddingsApiKey,
      advDirty,
      advValues,
    });
    onSave(payload);
    setApiKey("");
    setChatApiKey("");
    setVisionApiKey("");
    setEmbeddingsApiKey("");
  }

  function buildDraftPayload(useSavedSecret) {
    return {
      base_url: baseUrl,
      model,
      temperature: Number(temperature),
      timeout_seconds: Number(timeoutSeconds),
      use_saved_secret: useSavedSecret,
      ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}),
    };
  }

  function handleDraftTest() {
    onTestDraft(buildDraftPayload(apiKey.trim() ? false : true));
  }

  const saveDisabled = saving || Boolean(advancedValidationMessage) || !dirty;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 1,
          alignItems: "center",
        }}
      >
        <CursorPrimaryButton onClick={submit} disabled={saveDisabled}>
          {saving ? t("llm.save.saving") : t("llm.save.idle")}
        </CursorPrimaryButton>
        {advancedValidationMessage ? (
          <Typography sx={{ fontSize: "0.75rem", color: tk.control.dangerFg, flex: "1 1 200px" }}>
            {advancedValidationMessage}
          </Typography>
        ) : null}
      </Box>
      {saveError ? (
        <Alert severity="error" sx={alertMutedSx}>
          {saveError}
        </Alert>
      ) : null}

      <LlmProviderPresetsCard
        tk={tk}
        cardSx={cardSx}
        taskBaseUrls={{
          extraction: baseUrl,
          chat: chatBaseUrl,
          vision: vlBaseUrl,
          embeddings: embeddingsBaseUrl,
        }}
        onApplyPreset={applyProviderPreset}
      />

      <LlmTaskCard
        tk={tk}
        cardSx={cardSx}
        title={t("llm.card.extraction")}
        subtitle={t("llm.card.extractionHint")}
        headerExtra={<LlmTaskPresetActions tk={tk} task="extraction" onApply={applyPresetPatch} />}
      >
        <TextField
          label={t("llm.field.baseUrl")}
          size="small"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          sx={fieldSx}
          fullWidth
        />
        <TextField
          label={t("llm.field.model")}
          size="small"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          sx={fieldSx}
          fullWidth
        />
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 1.5 }}>
          <TextField
            label={t("llm.field.temperature")}
            size="small"
            value={temperature}
            onChange={(e) => setTemperature(e.target.value)}
            sx={fieldSx}
            fullWidth
          />
          <TextField
            label={`${t("llm.field.timeout")} (${t("llm.field.secondsSuffix")})`}
            size="small"
            value={timeoutSeconds}
            onChange={(e) => setTimeoutSeconds(e.target.value)}
            sx={fieldSx}
            fullWidth
            helperText={t("llm.hint.transportTimeout")}
          />
        </Box>
        <LlmSecretTextField
          label={t("llm.field.apiKey")}
          value={apiKey}
          onChange={setApiKey}
          fieldSx={fieldSx}
          placeholder={t("llm.card.apiKeyPlaceholder")}
          revealTask="extraction"
          savedPresent={hasSavedSecret}
        />
      </LlmTaskCard>

      <LlmTaskCard
        tk={tk}
        cardSx={cardSx}
        title={t("llm.card.chat")}
        subtitle={t("llm.hint.chatModelFallback")}
        headerExtra={<LlmTaskPresetActions tk={tk} task="chat" onApply={applyPresetPatch} />}
      >
        <TextField
          label={t("llm.field.chatModel")}
          size="small"
          value={chatModel}
          onChange={(e) => setChatModel(e.target.value)}
          sx={fieldSx}
          fullWidth
        />
        <TextField
          label={t("llm.field.chatBaseUrl")}
          size="small"
          value={chatBaseUrl}
          onChange={(e) => setChatBaseUrl(e.target.value)}
          sx={fieldSx}
          fullWidth
          placeholder={(llm?.effective?.resolved_chat_base_url || "").trim() || undefined}
        />
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 1.5 }}>
          <TextField
            label={t("llm.field.temperature")}
            size="small"
            value={chatTemperature}
            onChange={(e) => setChatTemperature(e.target.value)}
            sx={fieldSx}
            fullWidth
          />
          <TextField
            label={`${t("llm.field.timeout")} (${t("llm.field.secondsSuffix")})`}
            size="small"
            value={chatTimeoutSeconds}
            onChange={(e) => setChatTimeoutSeconds(e.target.value)}
            sx={fieldSx}
            fullWidth
          />
        </Box>
        <LlmSecretTextField
          label={t("llm.field.apiKey")}
          value={chatApiKey}
          onChange={setChatApiKey}
          fieldSx={fieldSx}
          placeholder={t("llm.card.chatKeyPlaceholder")}
          revealTask="chat"
          savedPresent={hasSavedChatSecret}
        />
      </LlmTaskCard>

      <LlmTaskCard
        tk={tk}
        cardSx={cardSx}
        title={t("llm.card.vision")}
        subtitle={t("llm.card.visionHint")}
        headerExtra={<LlmTaskPresetActions tk={tk} task="vision" onApply={applyPresetPatch} />}
      >
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 1.5 }}>
          <TextField
            label={t("llm.field.vlModel")}
            size="small"
            value={vlModel}
            onChange={(e) => setVlModel(e.target.value)}
            sx={fieldSx}
            fullWidth
            placeholder={(llm?.effective?.resolved_vl_model || "").trim() || undefined}
          />
          <TextField
            label={t("llm.field.vlBaseUrl")}
            size="small"
            value={vlBaseUrl}
            onChange={(e) => setVlBaseUrl(e.target.value)}
            sx={fieldSx}
            fullWidth
            helperText={t("llm.hint.vlBaseUrlFallback")}
            placeholder={(llm?.effective?.resolved_vl_base_url || "").trim() || undefined}
          />
        </Box>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 1.5 }}>
          <TextField
            label={t("llm.field.temperature")}
            size="small"
            value={vlTemperature}
            onChange={(e) => setVlTemperature(e.target.value)}
            sx={fieldSx}
            fullWidth
          />
          <TextField
            label={`${t("llm.field.timeout")} (${t("llm.field.secondsSuffix")})`}
            size="small"
            value={vlTimeoutSeconds}
            onChange={(e) => setVlTimeoutSeconds(e.target.value)}
            sx={fieldSx}
            fullWidth
          />
        </Box>
        <LlmSecretTextField
          label={t("llm.field.apiKey")}
          value={visionApiKey}
          onChange={setVisionApiKey}
          fieldSx={fieldSx}
          placeholder={t("llm.card.visionKeyPlaceholder")}
          revealTask="vision"
          savedPresent={hasSavedVisionSecret}
        />
      </LlmTaskCard>

      <LlmTaskCard
        tk={tk}
        cardSx={cardSx}
        title={t("llm.card.embeddings")}
        subtitle={t("llm.card.embeddingsHint")}
        headerExtra={<LlmTaskPresetActions tk={tk} task="embeddings" onApply={applyPresetPatch} />}
      >
        <TextField
          label={t("llm.field.baseUrl")}
          size="small"
          value={embeddingsBaseUrl}
          onChange={(e) => setEmbeddingsBaseUrl(e.target.value)}
          sx={fieldSx}
          fullWidth
        />
        <TextField
          label={t("llm.embeddings.model")}
          size="small"
          value={embeddingsModel}
          onChange={(e) => setEmbeddingsModel(e.target.value)}
          sx={fieldSx}
          fullWidth
          placeholder={(tasks.embeddings?.model_label || "").trim() || undefined}
        />
        <TextField
          label={`${t("llm.field.timeout")} (${t("llm.field.secondsSuffix")})`}
          size="small"
          value={embeddingsTimeoutSeconds}
          onChange={(e) => setEmbeddingsTimeoutSeconds(e.target.value)}
          sx={fieldSx}
          fullWidth
        />
        <LlmSecretTextField
          label={t("llm.field.apiKey")}
          value={embeddingsApiKey}
          onChange={setEmbeddingsApiKey}
          fieldSx={fieldSx}
          placeholder={t("llm.card.embeddingsKeyPlaceholder")}
          revealTask="embeddings"
          savedPresent={hasSavedEmbeddingsSecret}
        />
      </LlmTaskCard>

      <LlmConnectionTestCard
        disabled={!baseUrl || !model}
        testing={testing}
        result={testResult}
        onTestSaved={onTestSaved}
        onTestDraft={handleDraftTest}
      />

      <LlmAdvancedSettingsCard
        tk={tk}
        fieldSx={fieldSx}
        cardSx={cardSx}
        llm={llm}
        llmSchemaFields={llmSchemaFields}
        advValues={advValues}
        setAdvField={setAdvField}
        keysByGroup={keysByGroup}
        advancedOpen={advancedOpen}
        setAdvancedOpen={setAdvancedOpen}
        restoreRecommendedDefaults={restoreRecommendedDefaults}
      />
    </Box>
  );
}
