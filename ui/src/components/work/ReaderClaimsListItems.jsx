import React from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../i18n/useI18n.js";
import { READER_CLAIM_EVIDENCE_QUOTE_MAX, truncateWithEllipsis } from "./readerFormatters.js";

/**
 * @param {{
 *   layout: 'panel' | 'reader',
 *   claims: Array<Record<string, unknown>>,
 * }} props
 */
export default function ReaderClaimsListItems({ layout, claims }) {
  const { t } = useI18n();

  if (layout === "reader") {
    return (
      <>
        {claims.map((cl) => (
          <Box
            key={cl.claim_id}
            sx={{
              p: 1.25,
              borderRadius: "6px",
              border: "1px solid rgba(255,255,255,0.07)",
              backgroundColor: "#101010",
            }}
          >
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mb: 0.5 }}>
              <Chip label={cl.claim_type || "—"} size="small" sx={{ height: 22, fontSize: "0.65rem" }} />
              <Chip label={cl.polarity || "—"} size="small" variant="outlined" sx={{ height: 22, fontSize: "0.65rem" }} />
            </Box>
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)", whiteSpace: "pre-wrap" }}>
              {cl.normalized_text || ""}
            </Typography>
            {Array.isArray(cl.evidence) && cl.evidence.length > 0 ? (
              <Box sx={{ mt: 1 }}>
                <Typography sx={{ fontSize: "0.7rem", color: "rgba(129,140,248,0.85)", mb: 0.5 }}>{t("readerBody.claimsEvidence")}</Typography>
                {cl.evidence.map((ev, j) => {
                  const q = truncateWithEllipsis(ev.quote || "", READER_CLAIM_EVIDENCE_QUOTE_MAX);
                  return (
                    <Typography
                      key={`${cl.claim_id}-ev-${j}`}
                      sx={{
                        fontSize: "0.72rem",
                        color: "rgba(255,255,255,0.55)",
                        fontStyle: "italic",
                        mb: 0.5,
                        pl: 0.5,
                        borderLeft: "2px solid rgba(99,102,241,0.35)",
                      }}
                    >
                      {q.text}
                    </Typography>
                  );
                })}
              </Box>
            ) : null}
          </Box>
        ))}
      </>
    );
  }

  return (
    <>
      {claims.map((cl) => (
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
    </>
  );
}
