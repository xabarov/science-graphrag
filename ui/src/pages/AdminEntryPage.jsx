import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import AssessmentOutlinedIcon from "@mui/icons-material/AssessmentOutlined";
import ScienceOutlinedIcon from "@mui/icons-material/ScienceOutlined";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import TroubleshootOutlinedIcon from "@mui/icons-material/TroubleshootOutlined";

import { CursorIconAction, CursorSmallButton } from "../components/common/index.js";
import AdminApiStatusStrip from "./AdminApiStatusStrip.jsx";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";
import { useI18n } from "../i18n/useI18n.js";
import { getSetupHints } from "../services/setupHintsApi.js";

function AdminCard({ title, description, primaryTo, primaryLabel, primaryIcon, secondaryTo, secondaryLabel, secondaryIcon }) {
  const tk = useTheme().appTokens;
  return (
    <Box
      sx={{
        borderRadius: "6px",
        border: `1px solid ${tk.border.default}`,
        backgroundColor: tk.surface.panel,
        p: 2,
      }}
    >
      <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: tk.text.primary }}>{title}</Typography>
      <Typography sx={{ mt: 1, fontSize: "0.8125rem", color: tk.text.secondary, lineHeight: 1.55 }}>{description}</Typography>
      <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 0.75 }}>
        <CursorIconAction component={Link} to={primaryTo} title={primaryLabel}>
          {primaryIcon}
        </CursorIconAction>
        {secondaryTo ? (
          <CursorIconAction component={Link} to={secondaryTo} title={secondaryLabel}>
            {secondaryIcon}
          </CursorIconAction>
        ) : null}
      </Box>
    </Box>
  );
}

export default function AdminEntryPage() {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const [setupHints, setSetupHints] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const hints = await getSetupHints();
        if (!cancelled) setSetupHints(hints);
      } catch {
        if (!cancelled) setSetupHints(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Box sx={{ p: { xs: 1.5, sm: 0 }, ...mainShellContentSx }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: tk.text.primary, mb: 1 }}>{t("adminEntry.apiStatus")}</Typography>
      <AdminApiStatusStrip />
      {setupHints?.needs_initial_setup ? (
        <Alert
          severity="info"
          sx={{
            mb: 1.5,
            mt: 1,
            backgroundColor: tk.surface.panel,
            border: `1px solid ${tk.border.default}`,
            color: tk.text.primary,
            "& .MuiAlert-icon": { color: tk.text.secondary },
          }}
          action={
            <CursorSmallButton component={Link} to="/admin/settings" size="small">
              {t("home.setup.openSettings")}
            </CursorSmallButton>
          }
        >
          <Typography sx={{ fontSize: "0.8125rem", lineHeight: 1.55 }}>{t("home.setup.description")}</Typography>
        </Alert>
      ) : null}
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 1.5 }}>
        <AdminCard
          title={t("adminEntry.card.benchmarks.title")}
          description={t("adminEntry.card.benchmarks.description")}
          primaryTo="/admin/benchmarks"
          primaryLabel={t("adminEntry.card.benchmarks.primary")}
          primaryIcon={<AssessmentOutlinedIcon sx={{ fontSize: "1.1rem" }} />}
          secondaryTo="/admin/benchmarks?tab=analysis&analysisView=workbench"
          secondaryLabel={t("adminEntry.card.benchmarks.secondary")}
          secondaryIcon={<ScienceOutlinedIcon sx={{ fontSize: "1.1rem" }} />}
        />
        <AdminCard
          title={t("adminEntry.card.settings.title")}
          description={t("adminEntry.card.settings.description")}
          primaryTo="/admin/settings"
          primaryLabel={t("adminEntry.card.settings.primary")}
          primaryIcon={<SettingsOutlinedIcon sx={{ fontSize: "1.1rem" }} />}
        />
        <AdminCard
          title={t("adminEntry.card.diagnostics.title")}
          description={t("adminEntry.card.diagnostics.description")}
          primaryTo="/admin/diagnostics"
          primaryLabel={t("adminEntry.card.diagnostics.primary")}
          primaryIcon={<TroubleshootOutlinedIcon sx={{ fontSize: "1.1rem" }} />}
        />
      </Box>
    </Box>
  );
}
