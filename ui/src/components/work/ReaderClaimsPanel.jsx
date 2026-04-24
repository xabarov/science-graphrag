import React, { useEffect, useState } from "react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { formatResearchApiError, getWorkClaims } from "../../services/researchApi.js";
import { useI18n } from "../../i18n/I18nContext.jsx";

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
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!claimsUiEnabled() || !workId.trim()) {
      setItems([]);
      setError(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getWorkClaims(workId);
        if (cancelled) return;
        setItems(Array.isArray(res.data?.items) ? res.data.items : []);
      } catch (err) {
        if (cancelled) return;
        setError(formatResearchApiError(err));
        setItems([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workId]);

  if (!claimsUiEnabled()) {
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
        {!loading &&
          items.map((cl) => (
            <Box
              key={cl.claim_id}
              sx={{
                mb: 1.5,
                pb: 1.5,
                borderBottom: "1px solid rgba(255,255,255,0.06)",
                "&:last-child": { borderBottom: "none", pb: 0, mb: 0 },
              }}
            >
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center", mb: 0.5 }}>
                <Chip label={cl.claim_type || "—"} size="small" sx={{ height: 22, fontSize: "0.68rem" }} />
                <Chip label={cl.polarity || "—"} size="small" variant="outlined" sx={{ height: 22, fontSize: "0.68rem" }} />
                <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.4)" }}>
                  {t("wsTab.reader.claimConfidence", { v: String(cl.confidence ?? "—") })}
                </Typography>
              </Box>
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.82)", mb: 1 }}>{cl.normalized_text}</Typography>
              {(cl.evidence || []).map((ev, i) => (
                <Box
                  key={`${cl.claim_id}-ev-${i}`}
                  sx={{
                    mt: 0.75,
                    pl: 1,
                    borderLeft: "2px solid rgba(99,102,241,0.35)",
                  }}
                >
                  <Typography sx={{ fontSize: "0.7rem", color: "rgba(129,140,248,0.85)", fontFamily: "monospace" }}>
                    {ev.chunk_fingerprint || "—"}
                  </Typography>
                  {ev.section_path ? (
                    <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.4)" }}>{ev.section_path}</Typography>
                  ) : null}
                  <Typography sx={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.65)", mt: 0.35 }}>{ev.quote}</Typography>
                </Box>
              ))}
            </Box>
          ))}
      </AccordionDetails>
    </Accordion>
  );
}
