import React from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorPrimaryButton, CursorSmallButton } from "../components/common/index.js";
import AdminApiStatusStrip from "./AdminApiStatusStrip.jsx";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";
import { useI18n } from "../i18n/I18nContext.jsx";

function AdminCard({ title, description, primaryTo, primaryLabel, secondaryTo, secondaryLabel }) {
  return (
    <Box
      sx={{
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
        p: 2,
      }}
    >
      <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.9)" }}>{title}</Typography>
      <Typography sx={{ mt: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.58)", lineHeight: 1.55 }}>{description}</Typography>
      <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 1 }}>
        <CursorPrimaryButton component={Link} to={primaryTo} sx={{ textDecoration: "none" }}>
          {primaryLabel}
        </CursorPrimaryButton>
        {secondaryTo ? (
          <CursorSmallButton component={Link} to={secondaryTo} sx={{ textDecoration: "none" }}>
            {secondaryLabel}
          </CursorSmallButton>
        ) : null}
      </Box>
    </Box>
  );
}

export default function AdminEntryPage() {
  const { t } = useI18n();
  return (
    <Box sx={{ p: { xs: 1.5, sm: 0 }, ...mainShellContentSx }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.9)", mb: 1 }}>{t("adminEntry.apiStatus")}</Typography>
      <AdminApiStatusStrip />
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 1.5 }}>
        <AdminCard
          title={t("adminEntry.card.benchmarks.title")}
          description={t("adminEntry.card.benchmarks.description")}
          primaryTo="/admin/benchmarks"
          primaryLabel={t("adminEntry.card.benchmarks.primary")}
          secondaryTo="/admin/benchmarks?tab=workbench"
          secondaryLabel={t("adminEntry.card.benchmarks.secondary")}
        />
        <AdminCard
          title={t("adminEntry.card.settings.title")}
          description={t("adminEntry.card.settings.description")}
          primaryTo="/admin/settings"
          primaryLabel={t("adminEntry.card.settings.primary")}
        />
        <AdminCard
          title={t("adminEntry.card.diagnostics.title")}
          description={t("adminEntry.card.diagnostics.description")}
          primaryTo="/admin/diagnostics"
          primaryLabel={t("adminEntry.card.diagnostics.primary")}
        />
      </Box>
    </Box>
  );
}
