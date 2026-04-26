import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../i18n/I18nContext.jsx";
import { READER_COMBINED_MARKDOWN_MAX_CHARS, truncateWithEllipsis } from "./readerFormatters.js";

/**
 * @param {{ combinedMarkdown: string, chunks: { total?: number, items?: unknown[] } | null }} props
 */
export default function ReaderMarkdownSourcePanel({ combinedMarkdown, chunks }) {
  const { t } = useI18n();
  const { text: displayText } = truncateWithEllipsis(combinedMarkdown, READER_COMBINED_MARKDOWN_MAX_CHARS);
  const items = chunks?.items || [];
  const showPartial = chunks && Number(chunks.total) > items.length;

  return (
    <Box sx={{ mb: 2, p: 1.5, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#141414" }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 1 }}>{t("readerBody.extractedTitle")}</Typography>
      <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.42)", mb: 1 }}>{t("readerBody.extractedHint")}</Typography>
      <Box
        sx={{
          maxHeight: "min(60vh, 520px)",
          overflow: "auto",
          p: 1.25,
          borderRadius: "4px",
          border: "1px solid rgba(255,255,255,0.06)",
          backgroundColor: "#0a0a0a",
        }}
      >
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.82)", whiteSpace: "pre-wrap" }}>{displayText}</Typography>
      </Box>
      {showPartial ? (
        <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.38)", mt: 0.75 }}>
          {t("readerBody.chunksPartial", { shown: String(items.length), total: String(chunks.total) })}
        </Typography>
      ) : null}
    </Box>
  );
}
