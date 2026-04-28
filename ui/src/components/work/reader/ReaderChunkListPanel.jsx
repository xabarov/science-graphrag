import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";

import { CursorSmallButton } from "../../common/index.js";
import { useI18n } from "../../../i18n/useI18n.js";
import { READER_CHUNK_PREVIEW_MAX_CHARS, truncateWithEllipsis } from "./readerFormatters.js";

/**
 * @param {{
 *   chunks: { total?: number, items?: unknown[] } | null,
 *   chunksOpen: boolean,
 *   setChunksOpen: (fn: (b: boolean) => boolean) => void,
 *   orderedItems: unknown[],
 *   isChunkHighlighted: (ch: Record<string, unknown>) => boolean,
 * }} props
 */
export default function ReaderChunkListPanel({ chunks, chunksOpen, setChunksOpen, orderedItems, isChunkHighlighted }) {
  const { t } = useI18n();
  if (!chunks) return null;

  const countLabel = String(chunks.total ?? (chunks.items || []).length);

  return (
    <>
      <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.42)", mb: 1, lineHeight: 1.45 }}>
        {t("readerBody.chunksTraceHint")}
      </Typography>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, mb: 0.5 }}>
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{t("readerBody.chunksAdvanced", { count: countLabel })}</Typography>
        <CursorSmallButton type="button" onClick={() => setChunksOpen((o) => !o)} sx={{ fontSize: "0.75rem" }}>
          {chunksOpen ? t("readerBody.hide") : t("readerBody.show")}
        </CursorSmallButton>
      </Box>
      <Collapse in={chunksOpen}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {orderedItems.map((ch) => {
            const highlighted = isChunkHighlighted(ch);
            const preview = truncateWithEllipsis(ch?.text || "", READER_CHUNK_PREVIEW_MAX_CHARS);
            return (
              <Box
                key={`${ch.chunk_fingerprint}-${ch.order}`}
                sx={{
                  p: 1.5,
                  borderRadius: "6px",
                  border: highlighted ? "1px solid rgba(99,102,241,0.32)" : "1px solid rgba(255,255,255,0.08)",
                  backgroundColor: highlighted ? "rgba(99,102,241,0.08)" : "#141414",
                }}
              >
                <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.75 }}>
                  <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>
                    {t("readerBody.chunkMeta", {
                      section: ch.section_path || "—",
                      fp: String(ch.chunk_fingerprint || ""),
                    })}
                  </Typography>
                  {highlighted ? (
                    <Chip label={t("readerBody.focusedChip")} size="small" sx={{ height: 20, fontSize: "0.6875rem" }} />
                  ) : null}
                </Box>
                <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", mt: 0.5, whiteSpace: "pre-wrap" }}>
                  {preview.text}
                </Typography>
              </Box>
            );
          })}
        </Box>
      </Collapse>
    </>
  );
}
