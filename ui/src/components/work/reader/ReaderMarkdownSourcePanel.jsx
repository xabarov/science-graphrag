import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../i18n/useI18n.js";
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
 *   sourceVariant?: "extracted" | "extractedFile" | "abstract",
 *   apiTruncated?: boolean,
 * }} props
 */
export default function ReaderMarkdownSourcePanel({
  combinedMarkdown,
  chunks = null,
  sourceVariant = "extracted",
  apiTruncated = false,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const outerSx = useMemo(
    () => ({
      mb: 2,
      p: 1.5,
      borderRadius: "6px",
      border: `1px solid ${tk.border.default}`,
      backgroundColor: tk.surface.panel,
    }),
    [tk],
  );
  const innerSx = useMemo(
    () => ({
      minHeight: 240,
      overflow: "visible",
      p: { xs: 1.25, md: 2 },
      borderRadius: "4px",
      border: `1px solid ${tk.border.default}`,
      backgroundColor: tk.surface.code,
    }),
    [tk],
  );

  const maxChars = sourceVariant === "extracted" ? READER_COMBINED_MARKDOWN_MAX_CHARS : 0;
  const { text: displayText, truncated: displayTruncated } = truncateWithEllipsis(combinedMarkdown, maxChars);
  const items = chunks?.items || [];
  const showPartial = sourceVariant === "extracted" && chunks && Number(chunks.total) > items.length;
  const titleKey =
    sourceVariant === "abstract"
      ? "readerBody.abstractTitle"
      : sourceVariant === "extractedFile"
        ? "readerBody.extractedFileTitle"
        : "readerBody.extractedTitle";
  const hintKey =
    sourceVariant === "abstract"
      ? "readerBody.abstractHint"
      : sourceVariant === "extractedFile"
        ? "readerBody.extractedFileHint"
        : "readerBody.extractedHint";

  return (
    <Box sx={outerSx}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", mb: 1 }}>
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: tk.text.primary }}>{t(titleKey)}</Typography>
      </Box>
      <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, mb: 1 }}>{t(hintKey)}</Typography>
      <Box sx={innerSx}>
        <Box sx={{ width: "100%", maxWidth: "100%" }}>
          <MarkdownView markdown={displayText} data-testid="reader-markdown-body" />
        </Box>
      </Box>
      {showPartial ? (
        <Typography sx={{ fontSize: "0.7rem", color: tk.text.faint, mt: 0.75 }}>
          {t("readerBody.chunksPartial", { shown: String(items.length), total: String(chunks.total) })}
        </Typography>
      ) : null}
      {displayTruncated ? (
        <Typography sx={{ fontSize: "0.7rem", color: tk.text.faint, mt: 0.75 }}>
          {t("readerBody.readerMarkdownDisplayTruncated")}
        </Typography>
      ) : null}
      {apiTruncated && sourceVariant === "extractedFile" ? (
        <Typography sx={{ fontSize: "0.7rem", color: tk.text.faint, mt: 0.75 }}>
          {t("readerBody.extractedBodyTruncatedApi")}
        </Typography>
      ) : null}
    </Box>
  );
}
