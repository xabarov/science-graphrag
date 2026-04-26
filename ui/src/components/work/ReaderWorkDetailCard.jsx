import React, { useState } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../common/index.js";
import { useI18n } from "../../i18n/I18nContext.jsx";

/**
 * @param {{ detail: Record<string, unknown>, variant?: "default" | "rail" }} props
 */
export default function ReaderWorkDetailCard({ detail, variant = "default" }) {
  const { t } = useI18n();
  const [abstractOpen, setAbstractOpen] = useState(false);
  if (!detail) return null;

  const isRail = variant === "rail";

  return (
    <Box sx={{ mb: 2, p: 1.5, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a" }}>
      {!isRail ? (
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{detail.title || t("readerBody.noTitle")}</Typography>
      ) : null}
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mt: isRail ? 0 : 0.5 }}>
        {detail.year != null ? `${detail.year} · ` : ""}
        {detail.doi ? `DOI ${detail.doi} · ` : ""}
        {detail.arxiv_id ? `arXiv ${detail.arxiv_id}` : ""}
      </Typography>
      {detail.abstract ? (
        isRail ? (
          <Box sx={{ mt: 1 }}>
            <CursorSmallButton type="button" size="small" onClick={() => setAbstractOpen((o) => !o)} sx={{ mb: 0.5 }}>
              {abstractOpen ? t("readerBody.hideAbstract") : t("readerBody.showAbstract")}
            </CursorSmallButton>
            <Collapse in={abstractOpen}>
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)", mt: 0.5, whiteSpace: "pre-wrap" }}>
                {detail.abstract}
              </Typography>
            </Collapse>
          </Box>
        ) : (
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)", mt: 1, whiteSpace: "pre-wrap" }}>
            {detail.abstract}
          </Typography>
        )
      ) : null}
      {detail.ingestion ? (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 1 }}>
          {t("readerBody.ingestionLine", {
            docId: String(detail.ingestion.document_id ?? ""),
            hasChunks: String(detail.ingestion.has_chunks),
            semantic: String(detail.ingestion.has_semantic_layer),
          })}
        </Typography>
      ) : null}
    </Box>
  );
}
