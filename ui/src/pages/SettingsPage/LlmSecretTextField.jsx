import React, { useState } from "react";
import Visibility from "@mui/icons-material/Visibility";
import VisibilityOff from "@mui/icons-material/VisibilityOff";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import TextField from "@mui/material/TextField";

import { useI18n } from "../../i18n/useI18n.js";
import { formatResearchApiError } from "../../services/researchApi.js";
import { revealLlmTaskSecret } from "./settingsApi.js";

/**
 * Password-style API key field. The eye reveals the saved vault secret on first click,
 * then behaves as a normal show/hide toggle for the current field value.
 *
 * @param {{
 *   label: string,
 *   value: string,
 *   onChange: (v: string) => void,
 *   disabled?: boolean,
 *   fieldSx: object,
 *   placeholder?: string,
 *   autoComplete?: string,
 *   revealTask?: "extraction" | "chat" | "vision" | "embeddings" | null,
 *   savedPresent?: boolean,
 * }} props
 */
export default function LlmSecretTextField({
  label,
  value,
  onChange,
  disabled = false,
  fieldSx,
  placeholder,
  autoComplete = "new-password",
  revealTask = null,
  savedPresent = false,
}) {
  const { t } = useI18n();
  const [show, setShow] = useState(false);
  const [revealBusy, setRevealBusy] = useState(false);
  const [revealError, setRevealError] = useState("");

  async function revealSavedSecret() {
    setRevealBusy(true);
    setRevealError("");
    try {
      const secret = await revealLlmTaskSecret(revealTask);
      onChange(secret || "");
      setShow(true);
    } catch (err) {
      setRevealError(formatResearchApiError(err) || t("llm.secret.revealFailed"));
    } finally {
      setRevealBusy(false);
    }
  }

  function handleToggleVisibility() {
    if (!show && !value && revealTask && savedPresent) {
      void revealSavedSecret();
      return;
    }
    setShow((s) => !s);
  }

  return (
    <TextField
      label={label}
      type={show ? "text" : "password"}
      value={value}
      onChange={(e) => {
        setRevealError("");
        onChange(e.target.value);
      }}
      disabled={disabled}
      sx={fieldSx}
      fullWidth
      size="small"
      autoComplete={autoComplete}
      placeholder={placeholder}
      error={Boolean(revealError)}
      helperText={revealError || undefined}
      InputProps={{
        endAdornment: (
          <InputAdornment position="end" sx={{ gap: 0.5, flexWrap: "wrap", justifyContent: "flex-end" }}>
            <IconButton
              aria-label={t("llm.secret.toggleVisibility")}
              onClick={handleToggleVisibility}
              edge="end"
              size="small"
              disabled={disabled || revealBusy}
            >
              {show ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
            </IconButton>
          </InputAdornment>
        ),
      }}
    />
  );
}
