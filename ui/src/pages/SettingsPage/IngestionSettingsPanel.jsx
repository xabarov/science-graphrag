import React, { useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import FormHelperText from "@mui/material/FormHelperText";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { CursorPrimaryButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";

const FIELD_SX = {
  "& .MuiInputBase-root": {
    fontSize: "0.8125rem",
    backgroundColor: "rgba(255,255,255,0.02)",
  },
  "& .MuiOutlinedInput-notchedOutline": {
    borderColor: "rgba(255,255,255,0.12)",
  },
  "& .MuiInputBase-root:hover .MuiOutlinedInput-notchedOutline": {
    borderColor: "rgba(255,255,255,0.18)",
  },
  "& .MuiInputBase-root.Mui-focused .MuiOutlinedInput-notchedOutline": {
    borderColor: "rgba(99, 102, 241, 0.5)",
  },
  "& .MuiInputLabel-root": {
    fontSize: "0.8125rem",
    color: "rgba(255,255,255,0.6)",
  },
};

function IngestionSettingsPanelForm({
  resolved,
  claimsExtractionEnabled,
  saving,
  saveError,
  onSave,
  onDirtyChange,
}) {
  const { t } = useI18n();
  const [maxMb, setMaxMb] = useState(String(resolved));
  const [claimsEnabled, setClaimsEnabled] = useState(Boolean(claimsExtractionEnabled));

  const parsed = Number(maxMb);
  const inRange = Number.isFinite(parsed) && parsed >= 1 && parsed <= 2048;

  const dirty = useMemo(() => {
    return (
      Number(maxMb) !== Number(resolved) || Boolean(claimsEnabled) !== Boolean(claimsExtractionEnabled)
    );
  }, [claimsEnabled, claimsExtractionEnabled, maxMb, resolved]);

  useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!inRange) return;
    await onSave({
      max_file_size_mb: Math.floor(parsed),
      claims_extraction_enabled: Boolean(claimsEnabled),
    });
  }

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      sx={{
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
        borderRadius: 1.5,
        padding: 2.5,
        maxWidth: 560,
      }}
    >
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600 }}>{t("settings.ingestion.title")}</Typography>
      <Typography sx={{ marginTop: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.58)", lineHeight: 1.6 }}>
        {t("settings.ingestion.desc.p1")}{" "}
        <Typography component="span" sx={{ fontFamily: "ui-monospace, monospace", fontSize: "0.78rem" }}>
          {t("settings.ingestion.nginxDirective")}
        </Typography>{" "}
        {t("settings.ingestion.desc.p2")}
      </Typography>

      {saveError ? (
        <Alert
          severity="error"
          sx={{
            marginTop: 2,
            backgroundColor: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <Typography sx={{ fontSize: "0.8125rem" }}>{saveError}</Typography>
        </Alert>
      ) : null}

      <TextField
        label={t("settings.ingestion.maxFileSizeLabel")}
        type="number"
        value={maxMb}
        onChange={(e) => setMaxMb(e.target.value)}
        fullWidth
        sx={{ ...FIELD_SX, marginTop: 2.5 }}
        inputProps={{ min: 1, max: 2048, step: 1 }}
        required
      />
      <FormHelperText sx={{ color: "rgba(255,255,255,0.45)", fontSize: "0.75rem", marginTop: 0.75 }}>
        {t("settings.ingestion.rangeHint")}
      </FormHelperText>

      <Box
        sx={{
          marginTop: 2.5,
          padding: 1.5,
          borderRadius: 1.5,
          border: "1px solid rgba(255,255,255,0.08)",
          backgroundColor: "rgba(255,255,255,0.02)",
        }}
      >
        <FormControlLabel
          control={
            <Switch
              checked={claimsEnabled}
              onChange={(event) => setClaimsEnabled(event.target.checked)}
              color="default"
            />
          }
          label={t("settings.ingestion.claimsToggleLabel")}
          sx={{
            alignItems: "flex-start",
            margin: 0,
            "& .MuiFormControlLabel-label": {
              fontSize: "0.8125rem",
              color: "rgba(255,255,255,0.88)",
            },
          }}
        />
        <FormHelperText sx={{ color: "rgba(255,255,255,0.45)", fontSize: "0.75rem", marginTop: 0.5 }}>
          {t("settings.ingestion.claimsToggleHint")}
        </FormHelperText>
      </Box>

      <Box sx={{ marginTop: 2.5, display: "flex", gap: 1.5, flexWrap: "wrap" }}>
        <CursorPrimaryButton type="submit" disabled={saving || !dirty || !inRange}>
          {saving ? t("settings.ingestion.saveSaving") : t("settings.ingestion.saveButton")}
        </CursorPrimaryButton>
      </Box>
    </Box>
  );
}

export default function IngestionSettingsPanel({ ingestion, saving, saveError, onSave, onDirtyChange }) {
  const resolved = ingestion?.effective?.resolved_max_file_size_mb ?? ingestion?.max_file_size_mb ?? 128;
  const claimsExtractionEnabled =
    ingestion?.effective?.resolved_claims_extraction_enabled ??
    ingestion?.claims_extraction_enabled ??
    true;
  return (
    <IngestionSettingsPanelForm
      key={`${String(resolved)}:${String(claimsExtractionEnabled)}`}
      resolved={resolved}
      claimsExtractionEnabled={claimsExtractionEnabled}
      saving={saving}
      saveError={saveError}
      onSave={onSave}
      onDirtyChange={onDirtyChange}
    />
  );
}
