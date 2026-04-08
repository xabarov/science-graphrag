import React, { useCallback, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import { Link } from "react-router-dom";

import { CursorSmallButton } from "../components/common/index.js";
import { getHealth, getResearchApiBaseUrl } from "../services/researchApi.js";

export default function DiagnosticsPage() {
  const [status, setStatus] = useState("idle");
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setStatus("loading");
    setError(null);
    setPayload(null);
    try {
      const res = await getHealth();
      setPayload(res.data);
      setStatus("ok");
    } catch (e) {
      const msg = e?.response?.data?.detail
        ? JSON.stringify(e.response.data.detail)
        : e?.message || String(e);
      setError(msg);
      setStatus("error");
    }
  }, []);

  const baseHint = getResearchApiBaseUrl() || "(same origin — Vite dev proxies `/health` to the API port when configured)";

  return (
    <Box sx={{ maxWidth: 720 }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.9)", mb: 1 }}>
        Diagnostics
      </Typography>
      <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem", mb: 2 }}>
        Lightweight operational checks. Deep runtime metrics and status cards remain a follow-up; use{" "}
        <strong>Check health</strong> to call <code style={{ color: "rgba(129,140,248,0.95)" }}>GET /health</code> against
        the configured API base.
      </Typography>
      <Typography sx={{ color: "rgba(255,255,255,0.45)", fontSize: "0.75rem", mb: 2 }}>
        API base: <code style={{ color: "rgba(255,255,255,0.65)" }}>{baseHint}</code>
      </Typography>

      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 2 }}>
        <CursorSmallButton type="button" onClick={() => refresh()} disabled={status === "loading"}>
          {status === "loading" ? "Checking…" : "Check health"}
        </CursorSmallButton>
        <CursorSmallButton component={Link} to="/admin" sx={{ textDecoration: "none" }}>
          Back to admin
        </CursorSmallButton>
        <CursorSmallButton component={Link} to="/" sx={{ textDecoration: "none" }}>
          Home
        </CursorSmallButton>
      </Box>

      {status === "ok" && payload != null ? (
        <Alert severity="success" sx={{ fontSize: "0.8125rem", mb: 1 }}>
          Health check succeeded.
        </Alert>
      ) : null}
      {status === "error" && error ? (
        <Alert severity="error" sx={{ fontSize: "0.8125rem", mb: 1 }}>
          {error}
        </Alert>
      ) : null}
      {payload != null ? (
        <Box
          component="pre"
          sx={{
            m: 0,
            p: 1.5,
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.08)",
            backgroundColor: "rgba(0,0,0,0.25)",
            fontSize: "0.75rem",
            color: "rgba(255,255,255,0.65)",
            overflow: "auto",
          }}
        >
          {JSON.stringify(payload, null, 2)}
        </Box>
      ) : null}
    </Box>
  );
}
