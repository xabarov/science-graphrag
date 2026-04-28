import React, { useState } from "react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { useI18n } from "../../../i18n/useI18n.js";
import ReaderClaimsListItems from "./ReaderClaimsListItems.jsx";
import { useWorkClaims } from "./useWorkClaims.js";

function claimsUiEnabled() {
  const v = import.meta.env.VITE_CLAIMS_UI_ENABLED;
  return v === "1" || v === "true";
}

/**
 * Collapsible claims + evidence (Wave O). Hidden unless ``VITE_CLAIMS_UI_ENABLED=1``.
 * @param {{ workId: string }} props
 */
export default function ReaderClaimsPanel({ workId }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const uiEnabled = claimsUiEnabled();
  const { items, loading, error } = useWorkClaims(workId, {
    enabled: uiEnabled,
    fetchPolicy: "immediate",
  });

  if (!uiEnabled) {
    return null;
  }

  return (
    <Accordion
      expanded={open}
      onChange={(_e, expanded) => setOpen(expanded)}
      disableGutters
      sx={{
        mb: 2,
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: "8px !important",
        backgroundColor: "rgba(20,20,22,0.95)",
        "&:before": { display: "none" },
      }}
    >
      <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: "rgba(255,255,255,0.55)" }} />}>
        <Typography sx={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.85)" }}>{t("wsTab.reader.claimsTitle")}</Typography>
        {!loading && items.length > 0 ? (
          <Chip label={items.length} size="small" sx={{ ml: 1.5, height: 22, fontSize: "0.7rem" }} />
        ) : null}
      </AccordionSummary>
      <AccordionDetails sx={{ pt: 0 }}>
        {loading && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 1 }}>
            <CircularProgress size={20} sx={{ color: "rgba(129,140,248,0.9)" }} />
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("wsTab.reader.claimsLoading")}</Typography>
          </Box>
        )}
        {error && (
          <Alert severity="warning" sx={{ fontSize: "0.8125rem" }}>
            {error}
          </Alert>
        )}
        {!loading && !error && items.length === 0 ? (
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.45)" }}>{t("wsTab.reader.claimsEmpty")}</Typography>
        ) : null}
        {!loading && items.length > 0 ? <ReaderClaimsListItems layout="panel" claims={items} /> : null}
      </AccordionDetails>
    </Accordion>
  );
}
