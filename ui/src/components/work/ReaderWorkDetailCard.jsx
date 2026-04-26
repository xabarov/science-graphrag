import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../i18n/I18nContext.jsx";

/**
 * @param {{ detail: Record<string, unknown> }} props
 */
export default function ReaderWorkDetailCard({ detail }) {
  const { t } = useI18n();
  if (!detail) return null;

  return (
    <Box sx={{ mb: 2, p: 1.5, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a" }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{detail.title || t("readerBody.noTitle")}</Typography>
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mt: 0.5 }}>
        {detail.year != null ? `${detail.year} · ` : ""}
        {detail.doi ? `DOI ${detail.doi} · ` : ""}
        {detail.arxiv_id ? `arXiv ${detail.arxiv_id}` : ""}
      </Typography>
      {detail.abstract ? (
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)", mt: 1, whiteSpace: "pre-wrap" }}>
          {detail.abstract}
        </Typography>
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
