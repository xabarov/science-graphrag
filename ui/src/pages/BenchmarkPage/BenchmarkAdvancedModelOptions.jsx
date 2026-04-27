import React from "react";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

export default function BenchmarkAdvancedModelOptions({
  baseUrlOverride,
  apiKeyEnvName,
  onBaseUrlOverrideChange,
  onApiKeyEnvNameChange,
}) {
  const tk = useTheme().appTokens;
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
        gap: 1,
      }}
    >
      <TextField
        size="small"
        label="Base URL override"
        value={baseUrlOverride || ""}
        onChange={(e) => onBaseUrlOverrideChange?.(e.target.value)}
        placeholder="https://api.example.com/v1"
      />
      <TextField
        size="small"
        label="API key env var"
        value={apiKeyEnvName || ""}
        onChange={(e) => onApiKeyEnvNameChange?.(e.target.value)}
        placeholder="SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY"
      />
      <Typography
        sx={{
          gridColumn: "1 / -1",
          fontSize: "0.75rem",
          color: tk.text.muted,
        }}
      >
        The UI only sends the environment variable name. Secrets stay on the backend host.
      </Typography>
    </Box>
  );
}
