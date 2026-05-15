import React, { useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import FormHelperText from "@mui/material/FormHelperText";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { CursorDangerButton, CursorPrimaryButton, CursorSmallButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { credentialAlertBody, credentialAlertSeverity } from "./llmSettingsMeta.js";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   cardSx: object,
 *   fieldSx: object,
 *   alertMutedSx: object,
 *   llm: object,
 *   saving: boolean,
 *   testing: boolean,
 *   saveError: string | null,
 *   dirty: boolean,
 *   advancedValidationMessage: string,
 *   replaceKey: boolean,
 *   setReplaceKey: (v: boolean) => void,
 *   apiKey: string,
 *   setApiKey: (v: string) => void,
 *   revealDraftKey: boolean,
 *   setRevealDraftKey: (v: boolean) => void,
 *   replaceVisionKey: boolean,
 *   setReplaceVisionKey: (v: boolean) => void,
 *   visionApiKey: string,
 *   setVisionApiKey: (v: string) => void,
 *   revealVisionDraftKey: boolean,
 *   setRevealVisionDraftKey: (v: boolean) => void,
 *   onDeleteSecret: () => void,
 *   onDeleteVisionSecret: () => void,
 *   onSubmit: () => void,
 *   hasSavedSecret: boolean,
 *   hasSavedVisionSecret: boolean,
 * }} props
 */
export default function LlmSecretsCard({
  tk,
  cardSx,
  fieldSx,
  alertMutedSx,
  llm,
  saving,
  testing,
  saveError,
  dirty,
  advancedValidationMessage,
  replaceKey,
  setReplaceKey,
  apiKey,
  setApiKey,
  revealDraftKey,
  setRevealDraftKey,
  replaceVisionKey,
  setReplaceVisionKey,
  visionApiKey,
  setVisionApiKey,
  revealVisionDraftKey,
  setRevealVisionDraftKey,
  onDeleteSecret,
  onDeleteVisionSecret,
  onSubmit,
  hasSavedSecret,
  hasSavedVisionSecret,
}) {
  const { t } = useI18n();
  const st = llm?.status || {};
  const secretSource = st.secret_source;
  const alertSev = credentialAlertSeverity(secretSource, st.configured);
  const alertBody = credentialAlertBody(llm, t);
  const [diagOpen, setDiagOpen] = useState(false);
  const diag = llm?.diagnostics || {};
  const envVars = diag.operator_env_variables || [];

  const defaultReplaceHelper = hasSavedSecret
    ? t("llm.credentials.helperReplace")
    : secretSource === "environment"
      ? t("llm.credentials.helperSaveOverridesEnv")
      : t("llm.credentials.helperSaveFirst");

  const visionReplaceHelper = hasSavedVisionSecret
    ? t("llm.vision.helperReplace")
    : t("llm.vision.helperSaveFirst");

  return (
    <Box
      sx={{
        ...cardSx,
        padding: 2,
      }}
    >
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>
        {t("llm.secrets.title")}
      </Typography>
      <Typography sx={{ marginTop: 0.75, fontSize: "0.75rem", color: tk.text.secondary, lineHeight: 1.5 }}>
        {t("llm.secrets.intro")}
      </Typography>

      {st.vl_api_key_explicit_env && !hasSavedVisionSecret ? (
        <Alert severity="info" sx={{ marginTop: 2, ...alertMutedSx }}>
          <Typography sx={{ fontSize: "0.72rem" }}>{t("llm.vision.envSeparateHint")}</Typography>
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
          <Typography sx={{ fontSize: "0.72rem", color: tk.text.secondary, marginTop: 0.75 }}>{alertBody.hint}</Typography>
        ) : null}
        {(st.last_updated_at || st.last_updated_by) && hasSavedSecret ? (
          <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, marginTop: 0.75 }}>
            {[st.last_updated_by, st.last_updated_at].filter(Boolean).join(" • ")}
          </Typography>
        ) : null}
      </Alert>

      <Typography sx={{ marginTop: 2, fontSize: "0.8125rem", fontWeight: 600, color: tk.text.primary }}>
        {t("llm.secrets.defaultKeySection")}
      </Typography>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, marginTop: 1 }}>
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
          <FormHelperText sx={{ color: tk.text.muted }}>{defaultReplaceHelper}</FormHelperText>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, marginTop: 1 }}>
            <Switch checked={revealDraftKey} onChange={(e) => setRevealDraftKey(e.target.checked)} />
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>{t("llm.credentials.revealDraft")}</Typography>
          </Box>
        </Box>
      ) : null}

      <Typography sx={{ marginTop: 2.5, fontSize: "0.8125rem", fontWeight: 600, color: tk.text.primary }}>
        {t("llm.vision.title")}
      </Typography>
      <Typography sx={{ marginTop: 0.5, fontSize: "0.72rem", color: tk.text.muted, lineHeight: 1.5 }}>
        {t("llm.vision.intro")}
      </Typography>
      {llm?.tasks?.vision?.api_key?.masked ? (
        <Typography sx={{ marginTop: 0.75, fontSize: "0.72rem", color: tk.text.secondary }}>
          {t("llm.vision.maskedLine", { masked: llm.tasks.vision.api_key.masked })}
        </Typography>
      ) : null}

      <Box sx={{ display: "flex", alignItems: "center", gap: 1, marginTop: 1 }}>
        <Switch checked={replaceVisionKey} onChange={(e) => setReplaceVisionKey(e.target.checked)} />
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary }}>{t("llm.vision.setSwitch")}</Typography>
      </Box>
      {replaceVisionKey ? (
        <Box sx={{ marginTop: 1.5 }}>
          <TextField
            label={t("llm.vision.newKey")}
            size="small"
            type={revealVisionDraftKey ? "text" : "password"}
            value={visionApiKey}
            onChange={(e) => setVisionApiKey(e.target.value)}
            sx={fieldSx}
            fullWidth
          />
          <FormHelperText sx={{ color: tk.text.muted }}>{visionReplaceHelper}</FormHelperText>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, marginTop: 1 }}>
            <Switch checked={revealVisionDraftKey} onChange={(e) => setRevealVisionDraftKey(e.target.checked)} />
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>{t("llm.credentials.revealDraft")}</Typography>
          </Box>
        </Box>
      ) : null}

      <Box sx={{ marginTop: 1.5 }}>
        <CursorSmallButton type="button" onClick={() => setDiagOpen((v) => !v)}>
          {diagOpen ? t("llm.diagnostics.hide") : t("llm.diagnostics.show")}
        </CursorSmallButton>
        <Collapse in={diagOpen}>
          <Typography sx={{ marginTop: 1, fontSize: "0.6875rem", color: tk.text.muted, lineHeight: 1.5 }}>
            {diag.notes}
          </Typography>
          <Box sx={{ marginTop: 1, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
            {envVars.map((name) => (
              <Chip key={name} label={name} size="small" sx={{ fontSize: "0.65rem", height: 20 }} />
            ))}
          </Box>
        </Collapse>
      </Box>

      {advancedValidationMessage ? (
        <Alert severity="warning" sx={{ marginTop: 2, ...alertMutedSx }}>
          <Typography sx={{ fontSize: "0.75rem" }}>{advancedValidationMessage}</Typography>
        </Alert>
      ) : null}

      <Box sx={{ display: "flex", gap: 1, marginTop: 2, flexWrap: "wrap" }}>
        <CursorPrimaryButton onClick={onSubmit} disabled={saving || !dirty || Boolean(advancedValidationMessage)}>
          {saving ? t("llm.save.saving") : t("llm.save.idle")}
        </CursorPrimaryButton>
        <CursorDangerButton onClick={onDeleteSecret} disabled={saving || testing || !hasSavedSecret}>
          {t("llm.removeKey")}
        </CursorDangerButton>
        <CursorDangerButton onClick={onDeleteVisionSecret} disabled={saving || testing || !hasSavedVisionSecret}>
          {t("llm.vision.removeKey")}
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
  );
}
