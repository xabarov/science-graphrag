import React, { useCallback, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import { Link } from "react-router-dom";

import { CursorSmallButton } from "../components/common/index.js";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";
import { useI18n } from "../i18n/I18nContext.jsx";
import { formatResearchApiError, getHealth, getResearchApiBaseUrl, getWorks } from "../services/researchApi.js";

export default function DiagnosticsPage() {
  const { t } = useI18n();
  const [status, setStatus] = useState("idle");
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setStatus("loading");
    setError(null);
    setPayload(null);
    const combined = { health: null, works_catalog: null };
    try {
      const h = await getHealth();
      combined.health = h.data;
    } catch (e) {
      combined.health = { error: formatResearchApiError(e) };
    }
    try {
      const w = await getWorks({ limit: 1, offset: 0 });
      combined.works_catalog = {
        total: Number.isFinite(Number(w.data?.total)) ? Number(w.data.total) : null,
        ok: true,
      };
    } catch (e) {
      combined.works_catalog = { ok: false, error: formatResearchApiError(e) };
    }
    const healthFailed = combined.health && typeof combined.health === "object" && combined.health.error;
    const worksFailed = combined.works_catalog && combined.works_catalog.ok === false;
    if (healthFailed && worksFailed) {
      setError(`${combined.health.error} · ${combined.works_catalog.error}`);
      setStatus("error");
    } else {
      setPayload(combined);
      setStatus("ok");
    }
  }, []);

  const baseHint = getResearchApiBaseUrl() || "(same origin — Vite dev proxies `/health` to the API port when configured)";

  return (
    <Box sx={{ p: { xs: 1.5, sm: 2 }, ...mainShellContentSx }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.9)", mb: 1 }}>{t("diagnostics.title")}</Typography>
      <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem", mb: 2 }}>
        {t("diagnostics.intro")}
      </Typography>
      <Typography sx={{ color: "rgba(255,255,255,0.45)", fontSize: "0.75rem", mb: 2 }}>
        {t("diagnostics.apiBase")} <code style={{ color: "rgba(255,255,255,0.65)" }}>{baseHint}</code>
      </Typography>

      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 2 }}>
        <CursorSmallButton type="button" onClick={() => refresh()} disabled={status === "loading"}>
          {status === "loading" ? t("diagnostics.checking") : t("diagnostics.runChecks")}
        </CursorSmallButton>
        <CursorSmallButton component={Link} to="/admin" sx={{ textDecoration: "none" }}>
          {t("diagnostics.backAdmin")}
        </CursorSmallButton>
        <CursorSmallButton component={Link} to="/" sx={{ textDecoration: "none" }}>
          {t("diagnostics.home")}
        </CursorSmallButton>
      </Box>

      {status === "ok" && payload != null ? (
        <Alert severity="success" sx={{ fontSize: "0.8125rem", mb: 1 }}>
          {t("diagnostics.success")}
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
