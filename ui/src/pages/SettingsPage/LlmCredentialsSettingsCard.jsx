import React from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import FormHelperText from "@mui/material/FormHelperText";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { CursorDangerButton, CursorPrimaryButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   cardSx: object,
 *   fieldSx: object,
 *   alertMutedSx: object,
 *   llm: object,
 *   saving: boolean,
 *   saveError: string | null,
 *   dirty: boolean,
 *   advancedValidationMessage: string,
 *   replaceKey: boolean,
 *   setReplaceKey: (v: boolean) => void,
 *   apiKey: string,
 *   setApiKey: (v: string) => void,
 *   revealDraftKey: boolean,
 *   setRevealDraftKey: (v: boolean) => void,
 *   onDeleteSecret: () => void,
 *   onSubmit: () => void,
 *   alertSev: string,
 *   alertBody: { primary: string, hint: string | null },
 *   credentialsBlurbSecond: string,
 *   replaceHelper: string,
 *   hasSavedSecret: boolean,
 *   testing: boolean,
 * }} props
 */
export default function LlmCredentialsSettingsCard({
  tk,
  cardSx,
  fieldSx,
  alertMutedSx,
  llm,
  saving,
  saveError,
  dirty,
  advancedValidationMessage,
  replaceKey,
  setReplaceKey,
  apiKey,
  setApiKey,
  revealDraftKey,
  setRevealDraftKey,
  onDeleteSecret,
  onSubmit,
  alertSev,
  alertBody,
  credentialsBlurbSecond,
  replaceHelper,
  hasSavedSecret,
  testing,
}) {
  const { t } = useI18n();
  return (
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
      <Typography sx={{ marginTop: 0.5, fontSize: "0.72rem", color: tk.text.muted, lineHeight: 1.5 }}>{credentialsBlurbSecond}</Typography>

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
          <Typography sx={{ fontSize: "0.72rem", color: tk.text.secondary, marginTop: 0.75 }}>{alertBody.hint}</Typography>
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
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>{t("llm.credentials.revealDraft")}</Typography>
          </Box>
        </Box>
      ) : null}

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
