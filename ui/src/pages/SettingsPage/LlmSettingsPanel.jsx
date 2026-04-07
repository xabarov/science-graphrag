import React, { useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import FormHelperText from "@mui/material/FormHelperText";
import InputAdornment from "@mui/material/InputAdornment";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  CursorDangerButton,
  CursorPrimaryButton,
} from "../../components/common/index.js";
import LlmConnectionTestCard from "./LlmConnectionTestCard.jsx";

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

function providerSummary(llm) {
  const configured = llm?.status?.configured;
  const bits = [
    configured ? "Configured on server" : "No server key",
    llm?.effective?.resolved_model ? `Model ${llm.effective.resolved_model}` : null,
    llm?.effective?.resolved_base_url ? llm.effective.resolved_base_url : null,
  ].filter(Boolean);
  return bits.join(" • ");
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
  const [baseUrl, setBaseUrl] = useState(llm?.base_url || "");
  const [model, setModel] = useState(llm?.model || "");
  const [temperature, setTemperature] = useState(String(llm?.temperature ?? 0));
  const [timeoutSeconds, setTimeoutSeconds] = useState(String(llm?.effective?.resolved_timeout_seconds ?? 180));
  const [apiKey, setApiKey] = useState("");
  const [revealDraftKey, setRevealDraftKey] = useState(false);
  const [replaceKey, setReplaceKey] = useState(false);

  const dirty = useMemo(() => {
    return (
      baseUrl !== (llm?.base_url || "") ||
      model !== (llm?.model || "") ||
      Number(temperature) !== Number(llm?.temperature ?? 0) ||
      Number(timeoutSeconds) !== Number(llm?.effective?.resolved_timeout_seconds ?? 180) ||
      Boolean(apiKey) ||
      replaceKey
    );
  }, [apiKey, baseUrl, llm, model, replaceKey, temperature, timeoutSeconds]);

  React.useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);

  function submit() {
    onSave({
      base_url: baseUrl,
      model,
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

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
      <Box
        sx={{
          border: "1px solid rgba(255,255,255,0.08)",
          backgroundColor: "#1a1a1a",
          borderRadius: 1.5,
          padding: 2,
        }}
      >
        <Typography sx={{ fontSize: "0.875rem", fontWeight: 600 }}>LLM settings</Typography>
        <Typography sx={{ marginTop: 0.75, fontSize: "0.75rem", color: "rgba(255,255,255,0.58)", lineHeight: 1.5 }}>
          {providerSummary(llm)}
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
            label="Base URL"
            size="small"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            sx={FIELD_SX}
            fullWidth
          />
          <TextField
            label="Model"
            size="small"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            sx={FIELD_SX}
            fullWidth
          />
          <TextField
            label="Temperature"
            size="small"
            type="number"
            value={temperature}
            onChange={(e) => setTemperature(e.target.value)}
            sx={FIELD_SX}
            fullWidth
          />
          <TextField
            label="Timeout"
            size="small"
            type="number"
            value={timeoutSeconds}
            onChange={(e) => setTimeoutSeconds(e.target.value)}
            sx={FIELD_SX}
            fullWidth
            InputProps={{
              endAdornment: <InputAdornment position="end">s</InputAdornment>,
            }}
          />
        </Box>
      </Box>

      <Box
        sx={{
          border: "1px solid rgba(255,255,255,0.08)",
          backgroundColor: "#1a1a1a",
          borderRadius: 1.5,
          padding: 2,
        }}
      >
        <Typography sx={{ fontSize: "0.875rem", fontWeight: 600 }}>Credentials</Typography>
        <Typography sx={{ marginTop: 0.75, fontSize: "0.75rem", color: "rgba(255,255,255,0.58)", lineHeight: 1.5 }}>
          API key is stored securely on the server and is never returned to the browser after save.
        </Typography>

        <Alert
          severity={llm?.status?.configured ? "success" : "warning"}
          sx={{
            marginTop: 2,
            backgroundColor: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "rgba(255,255,255,0.85)",
            "& .MuiAlert-icon": { color: "inherit" },
          }}
        >
          <Typography sx={{ fontSize: "0.75rem" }}>
            {llm?.status?.configured
              ? `Configured on server${llm?.status?.masked_key ? ` (${llm.status.masked_key})` : ""}`
              : "No API key is currently configured on the server."}
          </Typography>
          {(llm?.status?.last_updated_at || llm?.status?.last_updated_by) && (
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.62)", marginTop: 0.5 }}>
              {[llm?.status?.last_updated_by, llm?.status?.last_updated_at].filter(Boolean).join(" • ")}
            </Typography>
          )}
        </Alert>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1, marginTop: 2 }}>
          <Switch checked={replaceKey} onChange={(e) => setReplaceKey(e.target.checked)} />
          <Typography sx={{ fontSize: "0.8125rem" }}>
            {llm?.status?.configured ? "Replace stored API key" : "Set API key"}
          </Typography>
        </Box>

        {replaceKey ? (
          <Box sx={{ marginTop: 1.5 }}>
            <TextField
              label="New API key"
              size="small"
              type={revealDraftKey ? "text" : "password"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              sx={FIELD_SX}
              fullWidth
            />
            <FormHelperText sx={{ color: "rgba(255,255,255,0.55)" }}>
              A new key will replace the existing secret.
            </FormHelperText>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, marginTop: 1 }}>
              <Switch checked={revealDraftKey} onChange={(e) => setRevealDraftKey(e.target.checked)} />
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)" }}>
                Reveal current draft only
              </Typography>
            </Box>
          </Box>
        ) : null}

        <Box sx={{ display: "flex", gap: 1, marginTop: 2, flexWrap: "wrap" }}>
          <CursorPrimaryButton onClick={submit} disabled={saving || !dirty}>
            {saving ? "Saving..." : "Save changes"}
          </CursorPrimaryButton>
          <CursorDangerButton onClick={onDeleteSecret} disabled={saving || testing || !llm?.status?.configured}>
            Remove key
          </CursorDangerButton>
        </Box>

        {saveError ? (
          <Alert
            severity="error"
            sx={{
              marginTop: 2,
              backgroundColor: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
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
