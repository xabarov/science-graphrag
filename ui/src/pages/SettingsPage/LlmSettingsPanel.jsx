import React, { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../i18n/useI18n.js";
import { outlinedAppTextFieldSx, settingsAlertMutedSx, settingsCardSx } from "../../theme/settingsFormSx.js";
import LlmAdvancedSettingsCard from "./LlmAdvancedSettingsCard.jsx";
import LlmConnectionTestCard from "./LlmConnectionTestCard.jsx";
import LlmQuickStartCard from "./LlmQuickStartCard.jsx";
import LlmSecretsCard from "./LlmSecretsCard.jsx";
import LlmTaskOverridesCard from "./LlmTaskOverridesCard.jsx";
import { computeSaveBlockingMessage } from "./llmSaveValidation.js";
import {
  buildAdvValuesFromLlm,
  buildLlmSettingsSubmitPayload,
  buildRuntimeOverridesPayload,
} from "./llmSettingsPayload.js";
import { LLM_RUNTIME_OVERRIDE_KEYS, schemaGroupForKey } from "./llmRuntimeOverrideKeys.js";

export default function LlmSettingsPanel({
  llm,
  schema,
  saving,
  testing,
  saveError,
  testResult,
  onSave,
  onDeleteSecret,
  onDeleteVisionSecret,
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
  const [vlModel, setVlModel] = useState("");
  const [vlBaseUrl, setVlBaseUrl] = useState("");
  const [temperature, setTemperature] = useState(String(llm?.temperature ?? 0));
  const [timeoutSeconds, setTimeoutSeconds] = useState(String(llm?.effective?.resolved_timeout_seconds ?? 180));
  const [apiKey, setApiKey] = useState("");
  const [revealDraftKey, setRevealDraftKey] = useState(false);
  const [replaceKey, setReplaceKey] = useState(false);
  const [visionApiKey, setVisionApiKey] = useState("");
  const [revealVisionDraftKey, setRevealVisionDraftKey] = useState(false);
  const [replaceVisionKey, setReplaceVisionKey] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [advValues, setAdvValues] = useState(() => buildAdvValuesFromLlm(llm));

  const hasSavedSecret = Boolean(llm?.status?.has_saved_secret);
  const hasSavedVisionSecret = Boolean(llm?.status?.has_saved_vision_secret);

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
    setChatModel(llm.chat_model || "");
    setVlModel((llm.vl_model || "").trim());
    setVlBaseUrl((llm.vl_base_url || "").trim());
    setTemperature(String(llm.temperature ?? 0));
    setTimeoutSeconds(String(llm.effective?.resolved_timeout_seconds ?? 180));
    setAdvValues(buildAdvValuesFromLlm(llm));
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
    const persistedVm = (llm?.vl_model || "").trim();
    const persistedVb = (llm?.vl_base_url || "").trim();
    return (
      baseUrl !== (llm?.base_url || "") ||
      model !== (llm?.model || "") ||
      chatModel !== (llm?.chat_model || "") ||
      vlModel.trim() !== persistedVm ||
      vlBaseUrl.trim() !== persistedVb ||
      Number(temperature) !== Number(llm?.temperature ?? 0) ||
      Number(timeoutSeconds) !== Number(llm?.effective?.resolved_timeout_seconds ?? 180) ||
      Boolean(apiKey) ||
      replaceKey
    );
  }, [
    apiKey,
    baseUrl,
    chatModel,
    llm,
    model,
    replaceKey,
    temperature,
    timeoutSeconds,
    vlBaseUrl,
    vlModel,
  ]);

  const visionKeyDirty = useMemo(() => replaceVisionKey && Boolean(visionApiKey.trim()), [replaceVisionKey, visionApiKey]);

  const dirty = providerDirty || advDirty || visionKeyDirty;

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

  function submit() {
    if (advancedValidationMessage) return;
    const payload = buildLlmSettingsSubmitPayload({
      baseUrl,
      model,
      chatModel,
      temperature: Number(temperature),
      timeoutSeconds: Number(timeoutSeconds),
      vlModel,
      vlBaseUrl,
      llm,
      replaceKey,
      apiKey,
      replaceVisionKey,
      visionApiKey,
      advDirty,
      advValues,
    });
    onSave(payload);
    setApiKey("");
    setReplaceKey(false);
    setRevealDraftKey(false);
    setVisionApiKey("");
    setReplaceVisionKey(false);
    setRevealVisionDraftKey(false);
  }

  function buildDraftPayload(useSavedSecret) {
    return {
      base_url: baseUrl,
      model,
      temperature: Number(temperature),
      timeout_seconds: Number(timeoutSeconds),
      use_saved_secret: useSavedSecret,
      ...(apiKey ? { api_key: apiKey } : {}),
    };
  }

  function handleDraftTest() {
    onTestDraft(buildDraftPayload(apiKey ? false : true));
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
      <LlmQuickStartCard
        tk={tk}
        cardSx={cardSx}
        fieldSx={fieldSx}
        llm={llm}
        baseUrl={baseUrl}
        setBaseUrl={setBaseUrl}
        temperature={temperature}
        setTemperature={setTemperature}
        timeoutSeconds={timeoutSeconds}
        setTimeoutSeconds={setTimeoutSeconds}
      />

      <LlmTaskOverridesCard
        tk={tk}
        cardSx={cardSx}
        fieldSx={fieldSx}
        llm={llm}
        model={model}
        setModel={setModel}
        chatModel={chatModel}
        setChatModel={setChatModel}
        vlModel={vlModel}
        setVlModel={setVlModel}
        vlBaseUrl={vlBaseUrl}
        setVlBaseUrl={setVlBaseUrl}
      />

      <LlmSecretsCard
        tk={tk}
        cardSx={cardSx}
        fieldSx={fieldSx}
        alertMutedSx={alertMutedSx}
        llm={llm}
        saving={saving}
        testing={testing}
        saveError={saveError}
        dirty={dirty}
        advancedValidationMessage={advancedValidationMessage}
        replaceKey={replaceKey}
        setReplaceKey={setReplaceKey}
        apiKey={apiKey}
        setApiKey={setApiKey}
        revealDraftKey={revealDraftKey}
        setRevealDraftKey={setRevealDraftKey}
        replaceVisionKey={replaceVisionKey}
        setReplaceVisionKey={setReplaceVisionKey}
        visionApiKey={visionApiKey}
        setVisionApiKey={setVisionApiKey}
        revealVisionDraftKey={revealVisionDraftKey}
        setRevealVisionDraftKey={setRevealVisionDraftKey}
        onDeleteSecret={onDeleteSecret}
        onDeleteVisionSecret={onDeleteVisionSecret}
        onSubmit={submit}
        hasSavedSecret={hasSavedSecret}
        hasSavedVisionSecret={hasSavedVisionSecret}
      />

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
