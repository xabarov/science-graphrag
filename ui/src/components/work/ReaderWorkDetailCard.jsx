import React, { useState } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { useI18n } from "../../i18n/useI18n.js";

/**
 * Compact work metadata card shown above the article body.
 * Abstract is collapsed by default so the reader stays focused on the
 * extracted text or PDF; toggle expands it inline. When the abstract is
 * already shown elsewhere (as the body fallback for chunkless works),
 * pass `hideAbstract` so the toggle is not duplicated.
 *
 * Re-syncs the toggle when the underlying work changes (`detail` identity)
 * or the default-expanded hint flips, using the "render-time state reset"
 * pattern so we avoid setState-in-effect cascades.
 *
 * @param {{
 *   detail: Record<string, unknown>,
 *   defaultAbstractExpanded?: boolean,
 *   hideAbstract?: boolean,
 * }} props
 */
export default function ReaderWorkDetailCard({
  detail,
  defaultAbstractExpanded = false,
  hideAbstract = false,
}) {
  const { t } = useI18n();
  const [abstractOpen, setAbstractOpen] = useState(Boolean(defaultAbstractExpanded));
  const [syncKey, setSyncKey] = useState(() => ({ detail, defaultAbstractExpanded }));

  if (syncKey.detail !== detail || syncKey.defaultAbstractExpanded !== defaultAbstractExpanded) {
    setSyncKey({ detail, defaultAbstractExpanded });
    setAbstractOpen(Boolean(defaultAbstractExpanded));
  }

  if (!detail) return null;

  const metaParts = [];
  if (detail.year != null) metaParts.push(String(detail.year));
  if (detail.doi) metaParts.push(`DOI ${detail.doi}`);
  if (detail.arxiv_id) metaParts.push(`arXiv ${detail.arxiv_id}`);
  const metaLine = metaParts.join(" · ");

  const hasAbstract = !hideAbstract && typeof detail.abstract === "string" && detail.abstract.trim().length > 0;
  const showCard = metaLine.length > 0 || hasAbstract;
  if (!showCard) return null;

  return (
    <Box
      sx={{
        mb: 2,
        p: 1.5,
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
      }}
    >
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1.5, rowGap: 0.5 }}>
        {metaLine ? (
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)" }}>{metaLine}</Typography>
        ) : null}
        {hasAbstract ? (
          <Box
            component="button"
            type="button"
            onClick={() => setAbstractOpen((o) => !o)}
            aria-expanded={abstractOpen}
            sx={{
              ml: metaLine ? "auto" : 0,
              display: "inline-flex",
              alignItems: "center",
              gap: 0.5,
              background: "transparent",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: "6px",
              color: "rgba(255,255,255,0.75)",
              cursor: "pointer",
              fontSize: "0.75rem",
              fontFamily: "inherit",
              padding: "2px 8px",
              transition: "all 0.15s ease",
              "&:hover": {
                borderColor: "rgba(255,255,255,0.2)",
                color: "rgba(255,255,255,0.92)",
                background: "rgba(255,255,255,0.04)",
              },
              "&:active": { transform: "scale(0.98)" },
            }}
          >
            {abstractOpen ? t("readerBody.hideAbstract") : t("readerBody.showAbstract")}
            <ExpandMoreIcon
              sx={{
                fontSize: "1rem",
                transition: "transform 0.15s ease",
                transform: abstractOpen ? "rotate(180deg)" : "rotate(0deg)",
              }}
            />
          </Box>
        ) : null}
      </Box>
      {hasAbstract ? (
        <Collapse in={abstractOpen} unmountOnExit>
          <Box sx={{ mt: 1.25, width: "100%" }}>
            <Typography
              sx={{
                fontSize: "0.8125rem",
                color: "rgba(255,255,255,0.78)",
                whiteSpace: "pre-wrap",
                width: "100%",
                maxWidth: "100%",
                lineHeight: 1.65,
                textAlign: "left",
              }}
            >
              {detail.abstract}
            </Typography>
          </Box>
        </Collapse>
      ) : null}
    </Box>
  );
}
