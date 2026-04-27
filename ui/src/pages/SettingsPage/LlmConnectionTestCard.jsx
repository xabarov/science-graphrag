import React, { useMemo } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorButton } from "../../components/common/index.js";
import { settingsAlertMutedSx, settingsCardSx } from "../../theme/settingsFormSx.js";

function toneForResult(result) {
  if (!result) return "info";
  if (result.status === "connected") return "success";
  if (result.status === "unexpected_response") return "warning";
  return "error";
}

export default function LlmConnectionTestCard({
  disabled,
  testing,
  result,
  onTestSaved,
  onTestDraft,
}) {
  const tk = useTheme().appTokens;
  const cardSx = useMemo(() => settingsCardSx(tk), [tk]);
  const alertMutedSx = useMemo(() => settingsAlertMutedSx(tk), [tk]);
  const tone = toneForResult(result);

  return (
    <Box
      sx={{
        ...cardSx,
        padding: 2,
      }}
    >
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>Connection test</Typography>
      <Typography sx={{ marginTop: 0.75, fontSize: "0.75rem", color: tk.text.secondary, lineHeight: 1.5 }}>
        Runs a minimal provider call and expects a simple OK response. Test output is not persisted.
      </Typography>

      <Box sx={{ display: "flex", gap: 1, marginTop: 2, flexWrap: "wrap" }}>
        <CursorButton onClick={onTestSaved} disabled={disabled || testing}>
          {testing ? "Testing..." : "Test saved config"}
        </CursorButton>
        <CursorButton onClick={onTestDraft} disabled={disabled || testing}>
          {testing ? "Testing..." : "Test draft config"}
        </CursorButton>
      </Box>

      {result ? (
        <Alert
          severity={tone}
          sx={{
            marginTop: 2,
            ...alertMutedSx,
          }}
        >
          <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600 }}>
            {result.status === "connected"
              ? "Connected"
              : result.status === "unexpected_response"
                ? "Unexpected response"
                : result.error_kind || "Connection error"}
          </Typography>
          <Typography sx={{ fontSize: "0.75rem", marginTop: 0.5, color: tk.text.primary }}>{result.message}</Typography>
          <Typography sx={{ fontSize: "0.75rem", marginTop: 1, color: tk.text.secondary }}>
            {[
              result.resolved?.base_url ? `Base URL: ${result.resolved.base_url}` : null,
              result.resolved?.model ? `Model: ${result.resolved.model}` : null,
              result.latency_ms != null ? `Latency: ${result.latency_ms} ms` : null,
              result.tested_at ? `Tested: ${result.tested_at}` : null,
            ]
              .filter(Boolean)
              .join(" | ")}
          </Typography>
        </Alert>
      ) : null}
    </Box>
  );
}
