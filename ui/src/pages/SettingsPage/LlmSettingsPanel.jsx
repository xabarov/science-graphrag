import React, { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../i18n/useI18n.js";
import { outlinedAppTextFieldSx, settingsAlertMutedSx, settingsCardSx } from "../../theme/settingsFormSx.js";
import LlmAdvancedSettingsCard from "./LlmAdvancedSettingsCard.jsx";
import LlmConnectionTestCard from "./LlmConnectionTestCard.jsx";
import LlmCredentialsSettingsCard from "./LlmCredentialsSettingsCard.jsx";
import LlmProviderSettingsCard from "./LlmProviderSettingsCard.jsx";
import { computeSaveBlockingMessage } from "./llmSaveValidation.js";
import { credentialAlertBody, credentialAlertSeverity, providerSummary } from "./llmSettingsMeta.js";
import { buildAdvValuesFromLlm, buildRuntimeOverridesPayload } from "./llmSettingsPayload.js";
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
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [advValues, setAdvValues] = useState(() => buildAdvValuesFromLlm(llm));

  const hasSavedSecret = Boolean(llm?.status?.has_saved_secret);
  const secretSource = llm?.status?.secret_source;

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
    const pVm = (llm.vl_model || "").trim();
    const pVb = (llm.vl_base_url || "").trim();
    setVlModel(pVm || (llm.effective?.resolved_vl_model ?? "") || "");
    setVlBaseUrl(pVb || (llm.effective?.resolved_vl_base_url ?? "") || "");
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

  const baselineVlModel = useMemo(() => {
    const p = (llm?.vl_model || "").trim();
    return p || (llm?.effective?.resolved_vl_model || "").trim();
  }, [llm]);

  const baselineVlBaseUrl = useMemo(() => {
    const p = (llm?.vl_base_url || "").trim();
    return p || (llm?.effective?.resolved_vl_base_url || "").trim();
  }, [llm]);

  const providerDirty = useMemo(() => {
    return (
      baseUrl !== (llm?.base_url || "") ||
      model !== (llm?.model || "") ||
      chatModel !== (llm?.chat_model || "") ||
      vlModel.trim() !== baselineVlModel ||
      vlBaseUrl.trim() !== baselineVlBaseUrl ||
      Number(temperature) !== Number(llm?.temperature ?? 0) ||
      Number(timeoutSeconds) !== Number(llm?.effective?.resolved_timeout_seconds ?? 180) ||
      Boolean(apiKey) ||
      replaceKey
    );
  }, [
    apiKey,
    baseUrl,
    baselineVlBaseUrl,
    baselineVlModel,
    chatModel,
    llm,
    model,
    replaceKey,
    temperature,
    timeoutSeconds,
    vlBaseUrl,
    vlModel,
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

  function submit() {
    if (advancedValidationMessage) return;
    const payload = {
      base_url: baseUrl,
      model,
      vl_model: vlModel.trim(),
      vl_base_url: vlBaseUrl.trim(),
      chat_model: chatModel.trim(),
      temperature: Number(temperature),
      timeout_seconds: Number(timeoutSeconds),
      ...(replaceKey && apiKey ? { api_key: apiKey } : {}),
    };
    if (advDirty) {
      payload.runtime_overrides = buildRuntimeOverridesPayload(advValues);
    }
    onSave(payload);
    setApiKey("");
    setReplaceKey(false);
    setRevealDraftKey(false);
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

  const alertBody = credentialAlertBody(llm, t);
  const alertSev = credentialAlertSeverity(secretSource, llm?.status?.configured);

  const credentialsBlurbSecond =
    secretSource === "server_managed"
      ? t("llm.credentials.blurbVault")
      : secretSource === "environment"
        ? t("llm.credentials.blurbEnv")
        : t("llm.credentials.blurbNone");

  const replaceHelper = hasSavedSecret
    ? t("llm.credentials.helperReplace")
    : secretSource === "environment"
      ? t("llm.credentials.helperSaveOverridesEnv")
      : t("llm.credentials.helperSaveFirst");

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
      <LlmProviderSettingsCard
        tk={tk}
        cardSx={cardSx}
        fieldSx={fieldSx}
        baseUrl={baseUrl}
        setBaseUrl={setBaseUrl}
        model={model}
        setModel={setModel}
        vlModel={vlModel}
        setVlModel={setVlModel}
        vlBaseUrl={vlBaseUrl}
        setVlBaseUrl={setVlBaseUrl}
        temperature={temperature}
        setTemperature={setTemperature}
        timeoutSeconds={timeoutSeconds}
        setTimeoutSeconds={setTimeoutSeconds}
        providerSummaryLine={providerSummary(llm, t)}
      />

      <LlmCredentialsSettingsCard
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
        onDeleteSecret={onDeleteSecret}
        onSubmit={submit}
        alertSev={alertSev}
        alertBody={alertBody}
        credentialsBlurbSecond={credentialsBlurbSecond}
        replaceHelper={replaceHelper}
        hasSavedSecret={hasSavedSecret}
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
        chatModel={chatModel}
        setChatModel={setChatModel}
        restoreRecommendedDefaults={restoreRecommendedDefaults}
      />
    </Box>
  );
}
