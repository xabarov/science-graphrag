import React, { useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import FormHelperText from "@mui/material/FormHelperText";
import InputAdornment from "@mui/material/InputAdornment";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import {
  CursorDangerButton,
  CursorPrimaryButton,
} from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import {
  outlinedAppTextFieldSx,
  settingsAlertMutedSx,
  settingsCardSx,
} from "../../theme/settingsFormSx.js";
import LlmConnectionTestCard from "./LlmConnectionTestCard.jsx";

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
  const [temperature, setTemperature] = useState(String(llm?.temperature ?? 0));
  const [timeoutSeconds, setTimeoutSeconds] = useState(String(llm?.effective?.resolved_timeout_seconds ?? 180));
  const [apiKey, setApiKey] = useState("");
  const [revealDraftKey, setRevealDraftKey] = useState(false);
  const [replaceKey, setReplaceKey] = useState(false);

  const hasSavedSecret = Boolean(llm?.status?.has_saved_secret);
  const secretSource = llm?.status?.secret_source;

  React.useEffect(() => {
    setChatModel(llm?.chat_model || "");
  }, [llm?.chat_model]);

  const dirty = useMemo(() => {
    return (
      baseUrl !== (llm?.base_url || "") ||
      model !== (llm?.model || "") ||
      chatModel !== (llm?.chat_model || "") ||
      Number(temperature) !== Number(llm?.temperature ?? 0) ||
      Number(timeoutSeconds) !== Number(llm?.effective?.resolved_timeout_seconds ?? 180) ||
      Boolean(apiKey) ||
      replaceKey
    );
  }, [apiKey, baseUrl, chatModel, llm, model, replaceKey, temperature, timeoutSeconds]);

  React.useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);

  function submit() {
    onSave({
      base_url: baseUrl,
      model,
      chat_model: chatModel.trim(),
      temperature: Number(temperature),
      timeout_seconds: Number(timeoutSeconds),
      ...(replaceKey && apiKey ? { api_key: apiKey } : {}),
    });
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
            label={t("llm.field.chatModel")}
            size="small"
            value={chatModel}
            onChange={(e) => setChatModel(e.target.value)}
            sx={fieldSx}
            fullWidth
            helperText={t("llm.hint.chatModelFallback")}
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

        <Box sx={{ display: "flex", gap: 1, marginTop: 2, flexWrap: "wrap" }}>
          <CursorPrimaryButton onClick={submit} disabled={saving || !dirty}>
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
    </Box>
  );
}
