import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../common/index.js";
import { useI18n } from "../../i18n/I18nContext.jsx";
import { READER_COMBINED_MARKDOWN_MAX_CHARS, truncateWithEllipsis } from "./readerFormatters.js";
import MarkdownView from "./MarkdownView.jsx";

/**
 * Reading view for the article body — renders the combined extracted markdown
 * (when chunks exist) or the abstract fallback (when chunks are missing) inside
 * a constrained measure for comfortable reading.
 *
 * @param {{
 *   combinedMarkdown: string,
 *   chunks?: { total?: number, items?: unknown[] } | null,
 *   sourceVariant?: "extracted" | "abstract",
 *   hasPdfFallback?: boolean,
 *   onOpenPdf?: () => void,
 * }} props
 */
export default function ReaderMarkdownSourcePanel({
  combinedMarkdown,
  chunks = null,
  sourceVariant = "extracted",
  hasPdfFallback = false,
  onOpenPdf,
}) {
  const { t } = useI18n();
  const { text: displayText } = truncateWithEllipsis(combinedMarkdown, READER_COMBINED_MARKDOWN_MAX_CHARS);
  const items = chunks?.items || [];
  const showPartial = sourceVariant === "extracted" && chunks && Number(chunks.total) > items.length;
  const titleKey = sourceVariant === "abstract" ? "readerBody.abstractTitle" : "readerBody.extractedTitle";
  const hintKey = sourceVariant === "abstract" ? "readerBody.abstractHint" : "readerBody.extractedHint";

  return (
    <Box
      sx={{
        mb: 2,
        p: 1.5,
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#141414",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", mb: 1 }}>
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{t(titleKey)}</Typography>
        <Box sx={{ flex: 1 }} />
        {sourceVariant === "abstract" && hasPdfFallback && typeof onOpenPdf === "function" ? (
          <CursorSmallButton type="button" size="small" onClick={onOpenPdf}>
            {t("readerBody.openPdf")}
          </CursorSmallButton>
        ) : null}
      </Box>
      <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.42)", mb: 1 }}>{t(hintKey)}</Typography>
      <Box
        sx={{
          maxHeight: "calc(100vh - 280px)",
          minHeight: 360,
          overflow: "auto",
          p: { xs: 1.25, md: 2 },
          borderRadius: "4px",
          border: "1px solid rgba(255,255,255,0.06)",
          backgroundColor: "#0a0a0a",
        }}
      >
        <Box sx={{ maxWidth: "78ch", mx: "auto" }}>
          <MarkdownView markdown={displayText} data-testid="reader-markdown-body" />
        </Box>
      </Box>
      {showPartial ? (
        <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.38)", mt: 0.75 }}>
          {t("readerBody.chunksPartial", { shown: String(items.length), total: String(chunks.total) })}
        </Typography>
      ) : null}
    </Box>
  );
}
