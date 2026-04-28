import React, { useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
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
import { useTheme } from "@mui/material/styles";

import {
  CursorDangerButton,
  CursorPrimaryButton,
  CursorSmallButton,
} from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import {
  outlinedAppTextFieldSx,
  settingsAlertMutedSx,
  settingsCardSx,
} from "../../theme/settingsFormSx.js";
import LlmConnectionTestCard from "./LlmConnectionTestCard.jsx";
import {
  LLM_ADVANCED_GROUPS,
  LLM_RUNTIME_OVERRIDE_KEYS,
  schemaGroupForKey,
} from "./llmRuntimeOverrideKeys.js";

const AGENT_RUNTIME_SLUGS = ["langgraph_research_v1", "langgraph_supervisor_v1", "retrieval_v1"];

function advancedFieldLabel(t, key) {
  const i18nKey = `llm.advanced.field.${key}`;
  const label = t(i18nKey);
  return label !== i18nKey ? label : key;
}

/** Provider transport + advanced numeric and cross-field rules (Phase 3). */
function computeSaveBlockingMessage(t, advValues, timeoutSeconds) {
  const transport = Number(timeoutSeconds);
  if (!Number.isFinite(transport) || transport < 1) {
    return t("llm.field.error.invalidTimeout");
  }
  for (const k of LLM_RUNTIME_OVERRIDE_KEYS) {
    if (
      k === "agent_turn_policy_llm_enabled" ||
      k === "agent_runtime" ||
      k === "llm_distributed_quota_enabled" ||
      k === "llm_distributed_quota_key_prefix"
    )
      continue;
    if (!(k in advValues)) continue;
    const raw = advValues[k];
    if (String(raw).trim() === "") {
      return t("llm.advanced.error.emptyNumeric");
    }
    const num = Number(raw);
    if (!Number.isFinite(num)) {
      return t("llm.advanced.error.invalidNumeric");
    }
  }
  const classifier = Number(advValues.agent_turn_policy_classifier_timeout_seconds);
  const step = Number(advValues.agent_step_timeout_seconds);
  if (Number.isFinite(classifier) && Number.isFinite(transport) && classifier > transport) {
    return t("llm.advanced.error.classifierGtTransport");
  }
  if (Number.isFinite(classifier) && Number.isFinite(step) && step < classifier) {
    return t("llm.advanced.error.stepLtClassifier");
  }
  const distOn =
    advValues.llm_distributed_quota_enabled === "1" || advValues.llm_distributed_quota_enabled === "true";
  if (distOn) {
    const pfx = String(advValues.llm_distributed_quota_key_prefix ?? "").trim();
    if (!pfx) {
      return t("llm.advanced.error.distributedPrefixRequired");
    }
  }
  return "";
}

function buildAdvValuesFromLlm(llm) {
  const ac = llm?.advanced_controls;
  const o = {};
  if (!ac) return o;
  for (const k of LLM_RUNTIME_OVERRIDE_KEYS) {
    const cell = ac[k];
    if (!cell) continue;
    if (k === "agent_turn_policy_llm_enabled" || k === "llm_distributed_quota_enabled") {
      o[k] = cell.effective ? "1" : "0";
    } else {
      o[k] = String(cell.effective);
    }
  }
  return o;
}

function buildRuntimeOverridesPayload(advValues) {
  const o = {};
  for (const k of LLM_RUNTIME_OVERRIDE_KEYS) {
    if (!(k in advValues)) continue;
    const raw = advValues[k];
    if (k === "agent_turn_policy_llm_enabled" || k === "llm_distributed_quota_enabled") {
      o[k] = raw === "1" || raw === "true" || raw === true;
      continue;
    }
    if (k === "llm_distributed_quota_key_prefix") {
      o[k] = String(raw || "").trim();
      continue;
    }
    if (k === "agent_runtime") {
      o[k] = String(raw || "").trim();
      continue;
    }
    if (
      k === "agent_step_timeout_seconds" ||
      k === "agent_turn_policy_classifier_timeout_seconds" ||
      k === "work_dedup_llm_timeout_s" ||
      k === "author_dedup_llm_timeout_s" ||
      k === "llm_distributed_quota_acquire_timeout_seconds"
    ) {
      const n = Number(raw);
      if (!Number.isFinite(n)) continue;
      o[k] = n;
    } else {
      const n = parseInt(String(raw), 10);
      if (!Number.isFinite(n)) continue;
      o[k] = n;
    }
  }
  return o;
}

function providerSummary(llm, t) {
  const bits = [];
  const configured = llm?.status?.configured;
  const src = llm?.status?.secret_source;
  if (configured) {
    if (src === "server_managed") bits.push(t("llm.summary.sourceServer"));
    else if (src === "environment") bits.push(t("llm.summary.sourceEnv"));
    else bits.push(t("llm.summary.hasCredential"));
  } else {
    bits.push(t("llm.summary.noCredential"));
  }
  if (llm?.effective?.resolved_model) {
    bits.push(t("llm.summary.model", { model: llm.effective.resolved_model }));
  }
  if (llm?.effective?.resolved_chat_model) {
    bits.push(t("llm.summary.chatModel", { model: llm.effective.resolved_chat_model }));
  }
  if (llm?.effective?.resolved_base_url) {
    bits.push(llm.effective.resolved_base_url);
  }
  return bits.filter(Boolean).join(" • ");
}

function credentialAlertSeverity(secretSource, configured) {
  if (!configured) return "warning";
  if (secretSource === "environment") return "info";
  return "success";
}

function credentialAlertBody(llm, t) {
  const st = llm?.status || {};
  const configured = st.configured;
  const src = st.secret_source;
  const masked = st.masked_key;
  const maskedSuffix = masked ? ` (${masked})` : "";

  if (!configured) {
    return { primary: t("llm.credentials.none"), hint: null };
  }
  if (src === "environment") {
    return {
      primary: t("llm.credentials.fromEnv", { masked: maskedSuffix }),
      hint: st.env_key_hint || null,
    };
  }
  return {
    primary: t("llm.credentials.fromServer", { masked: maskedSuffix }),
    hint: null,
  };
}

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
          {fieldHelper(key) ? (
            <FormHelperText sx={{ color: tk.text.muted }}>{fieldHelper(key)}</FormHelperText>
          ) : null}
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
              <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, marginTop: 0.25 }}>
                {fieldHelper(key)}
              </Typography>
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
      <Box
        sx={{
          ...cardSx,
          padding: 2,
        }}
      >
        <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>{t("llm.panel.title")}</Typography>
        <Typography sx={{ marginTop: 0.75, fontSize: "0.75rem", color: tk.text.secondary, lineHeight: 1.5 }}>
          {providerSummary(llm, t)}
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
          <TextField
            label={t("llm.field.model")}
            size="small"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            sx={fieldSx}
            fullWidth
          />
          <TextField
            label={t("llm.field.vlModel")}
            size="small"
            value={vlModel}
            onChange={(e) => setVlModel(e.target.value)}
            sx={fieldSx}
            fullWidth
          />
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

      <Box
        sx={{
          ...cardSx,
          padding: 2,
        }}
      >
        <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>{t("llm.credentials.title")}</Typography>
        <Typography sx={{ marginTop: 0.75, fontSize: "0.75rem", color: tk.text.secondary, lineHeight: 1.5 }}>
          {t("llm.credentials.blurbLead")}
        </Typography>
        <Typography sx={{ marginTop: 0.5, fontSize: "0.72rem", color: tk.text.muted, lineHeight: 1.5 }}>
          {credentialsBlurbSecond}
        </Typography>

        {llm?.status?.vl_api_key_explicit_env ? (
          <Alert severity="info" sx={{ marginTop: 2, ...alertMutedSx }}>
            <Typography sx={{ fontSize: "0.72rem" }}>{t("llm.credentials.vlEnvOverride")}</Typography>
          </Alert>
        ) : null}

        <Alert
          severity={alertSev}
          sx={{
            marginTop: 2,
            ...alertMutedSx,
          }}
        >
          <Typography sx={{ fontSize: "0.75rem" }}>{alertBody.primary}</Typography>
          {alertBody.hint ? (
            <Typography sx={{ fontSize: "0.72rem", color: tk.text.secondary, marginTop: 0.75 }}>
              {alertBody.hint}
            </Typography>
          ) : null}
          {(llm?.status?.last_updated_at || llm?.status?.last_updated_by) && hasSavedSecret ? (
            <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, marginTop: 0.75 }}>
              {[llm?.status?.last_updated_by, llm?.status?.last_updated_at].filter(Boolean).join(" • ")}
            </Typography>
          ) : null}
        </Alert>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1, marginTop: 2 }}>
          <Switch checked={replaceKey} onChange={(e) => setReplaceKey(e.target.checked)} />
          <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary }}>
            {hasSavedSecret ? t("llm.credentials.replaceSwitch") : t("llm.credentials.setSwitch")}
          </Typography>
        </Box>

        {replaceKey ? (
          <Box sx={{ marginTop: 1.5 }}>
            <TextField
              label={t("llm.credentials.newKey")}
              size="small"
              type={revealDraftKey ? "text" : "password"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              sx={fieldSx}
              fullWidth
            />
            <FormHelperText sx={{ color: tk.text.muted }}>{replaceHelper}</FormHelperText>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, marginTop: 1 }}>
              <Switch checked={revealDraftKey} onChange={(e) => setRevealDraftKey(e.target.checked)} />
              <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>
                {t("llm.credentials.revealDraft")}
              </Typography>
            </Box>
          </Box>
        ) : null}

        {advancedValidationMessage ? (
          <Alert severity="warning" sx={{ marginTop: 2, ...alertMutedSx }}>
            <Typography sx={{ fontSize: "0.75rem" }}>{advancedValidationMessage}</Typography>
          </Alert>
        ) : null}

        <Box sx={{ display: "flex", gap: 1, marginTop: 2, flexWrap: "wrap" }}>
          <CursorPrimaryButton onClick={submit} disabled={saving || !dirty || Boolean(advancedValidationMessage)}>
            {saving ? t("llm.save.saving") : t("llm.save.idle")}
          </CursorPrimaryButton>
          <CursorDangerButton onClick={onDeleteSecret} disabled={saving || testing || !hasSavedSecret}>
            {t("llm.removeKey")}
          </CursorDangerButton>
        </Box>

        {saveError ? (
          <Alert
            severity="error"
            sx={{
              marginTop: 2,
              ...alertMutedSx,
            }}
          >
            <Typography sx={{ fontSize: "0.75rem" }}>{saveError}</Typography>
          </Alert>
        ) : null}
      </Box>

      <LlmConnectionTestCard
        disabled={!baseUrl || !model}
        testing={testing}
        result={testResult}
        onTestSaved={onTestSaved}
        onTestDraft={handleDraftTest}
      />

      <Box sx={{ ...cardSx, padding: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, flexWrap: "wrap" }}>
          <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>
            {t("llm.advanced.title")}
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Switch checked={advancedOpen} onChange={(e) => setAdvancedOpen(e.target.checked)} />
            <Typography sx={{ fontSize: "0.8125rem", color: tk.text.secondary }}>{t("llm.advanced.toggle")}</Typography>
          </Box>
        </Box>
        <Typography sx={{ marginTop: 0.75, fontSize: "0.72rem", color: tk.text.muted, lineHeight: 1.5 }}>
          {t("llm.advanced.intro")}
        </Typography>
        <Collapse in={advancedOpen}>
          <Box
            sx={{
              marginTop: 1.5,
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
              gap: 1.5,
            }}
          >
            <TextField
              label={t("llm.field.chatModel")}
              size="small"
              value={chatModel}
              onChange={(e) => setChatModel(e.target.value)}
              sx={fieldSx}
              fullWidth
              helperText={t("llm.hint.chatModelFallback")}
            />
          </Box>
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
    </Box>
  );
}
