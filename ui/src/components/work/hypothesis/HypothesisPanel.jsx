import React from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import AgentToolTrace from "./AgentToolTrace.jsx";
import { useI18n } from "../../i18n/useI18n.js";

export default function HypothesisPanel({
  hypotheses = [],
  contradictions = [],
  toolTrace = [],
  loading = false,
  error = "",
}) {
  const { t } = useI18n();
  if (loading) {
    return (
      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.7)" }}>
        {t("askPanel.idea.loadingCandidates")}
      </Typography>
    );
  }
  if (error) {
    return (
      <Alert severity="error" sx={{ fontSize: "0.8125rem" }}>
        {error}
      </Alert>
    );
  }

  const hasHypotheses = Array.isArray(hypotheses) && hypotheses.length > 0;
  const hasContradictions = Array.isArray(contradictions) && contradictions.length > 0;
  if (!hasHypotheses && !hasContradictions) {
    return (
      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.65)" }}>
        {t("askPanel.idea.noCandidates")}
      </Typography>
    );
  }

  return (
    <Box sx={{ display: "grid", gap: 1.25 }}>
      <Alert
        severity="info"
        sx={{
          fontSize: "0.75rem",
          backgroundColor: "rgba(99,102,241,0.08)",
          color: "rgba(255,255,255,0.85)",
          border: "1px solid rgba(99,102,241,0.22)",
        }}
      >
        {t("askPanel.idea.advisory")}
      </Alert>
      {hasHypotheses ? (
        <Box sx={{ display: "grid", gap: 1 }}>
          {hypotheses.map((item, idx) => (
            <Box
              key={`hyp-${idx}`}
              sx={{
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: "6px",
                p: 1.25,
                backgroundColor: "rgba(255,255,255,0.02)",
              }}
            >
                <Typography sx={{ fontSize: "0.82rem", color: "rgba(255,255,255,0.92)" }}>
                {idx + 1}. {item?.text || t("common.emDash")}
              </Typography>
              {item?.novelty_hint ? (
                <Typography sx={{ mt: 0.5, fontSize: "0.74rem", color: "rgba(129,140,248,0.95)" }}>
                  {t("askPanel.idea.noveltyHint")} {item.novelty_hint}
                </Typography>
              ) : null}
              {Array.isArray(item?.supporting_claim_ids) && item.supporting_claim_ids.length > 0 ? (
                <Typography sx={{ mt: 0.5, fontSize: "0.72rem", color: "rgba(255,255,255,0.58)" }}>
                  {t("askPanel.idea.claims")} {item.supporting_claim_ids.join(", ")}
                </Typography>
              ) : null}
              {Array.isArray(item?.evidence_quotes) && item.evidence_quotes.length > 0 ? (
                <Box sx={{ mt: 0.75, pl: 1, borderLeft: "1px solid rgba(255,255,255,0.12)" }}>
                  {item.evidence_quotes.slice(0, 3).map((quote, qIdx) => (
                    <Typography key={`q-${idx}-${qIdx}`} sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.66)" }}>
                      &quot;{quote}&quot;
                    </Typography>
                  ))}
                </Box>
              ) : null}
            </Box>
          ))}
        </Box>
      ) : null}
      {hasContradictions ? (
        <Box
          sx={{
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: "6px",
            p: 1.25,
            backgroundColor: "rgba(255,255,255,0.02)",
          }}
        >
          <Typography sx={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.84)", mb: 0.5 }}>
            {t("askPanel.idea.contradictionCandidates")}
          </Typography>
          {contradictions.map((item, idx) => (
            <Typography key={`c-${idx}`} sx={{ fontSize: "0.74rem", color: "rgba(255,255,255,0.68)" }}>
              {`${item?.claim_a_id || "?"} ↔ ${item?.claim_b_id || "?"}: ${item?.description || ""}`}
            </Typography>
          ))}
        </Box>
      ) : null}
      <AgentToolTrace toolTrace={toolTrace} />
    </Box>
  );
}
