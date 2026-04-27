import React, { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../i18n/useI18n.js";
import { getHealth, getWorks } from "../services/researchApi.js";

/** Lightweight read-only probes for the admin hub (no secrets). */
export default function AdminApiStatusStrip() {
  const { t, locale } = useI18n();
  const tk = useTheme().appTokens;
  const [row, setRow] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const out = { healthLabel: "—", worksLabel: "—" };
      try {
        const h = await getHealth();
        if (!cancelled) {
          out.healthLabel = h.data?.status === "ok" ? "OK" : JSON.stringify(h.data);
        }
      } catch {
        if (!cancelled) out.healthLabel = t("adminApi.unreachable");
      }
      try {
        const w = await getWorks({ limit: 1, offset: 0 });
        if (!cancelled) {
          const tot = w.data?.total;
          out.worksLabel = Number.isFinite(Number(tot))
            ? t("adminApi.catalogTotal", { total: Number(tot) })
            : t("adminApi.reachable");
        }
      } catch {
        if (!cancelled) out.worksLabel = t("adminApi.unreachable");
      }
      if (!cancelled) setRow(out);
    })();
    return () => {
      cancelled = true;
    };
  }, [t, locale]);

  if (!row) {
    return (
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 2 }}>
        {t("adminApi.loading")}
      </Typography>
    );
  }

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
        gap: 1,
        mb: 2,
      }}
      role="status"
      aria-live="polite"
    >
      <Box
        sx={{
          p: 1.25,
          borderRadius: "6px",
          border: `1px solid ${tk.border.default}`,
          backgroundColor: tk.surface.sidebar,
        }}
      >
        <Typography sx={{ fontSize: "0.6875rem", color: tk.text.muted, mb: 0.5 }}>{t("adminApi.health")}</Typography>
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, fontFamily: "monospace" }}>{row.healthLabel}</Typography>
      </Box>
      <Box
        sx={{
          p: 1.25,
          borderRadius: "6px",
          border: `1px solid ${tk.border.default}`,
          backgroundColor: tk.surface.sidebar,
        }}
      >
        <Typography sx={{ fontSize: "0.6875rem", color: tk.text.muted, mb: 0.5 }}>{t("adminApi.works")}</Typography>
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, fontFamily: "monospace" }}>{row.worksLabel}</Typography>
      </Box>
    </Box>
  );
}
