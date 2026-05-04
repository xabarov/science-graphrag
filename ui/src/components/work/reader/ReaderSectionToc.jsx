import React from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../../i18n/useI18n.js";

/**
 * Jump links to chunk sections (scrolls first matching chunk row into view).
 *
 * @param {{ sections: string[], orderedItems: Array<Record<string, unknown>>, onOpenChunks?: () => void }} props
 */
export default function ReaderSectionToc({ sections, orderedItems, onOpenChunks }) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  if (!sections.length) return null;

  function scrollToSection(section) {
    const idx = orderedItems.findIndex((ch) => String(ch?.section_path || "").trim() === section);
    if (idx < 0) return;
    onOpenChunks?.();
    requestAnimationFrame(() => {
      const el = document.getElementById(`reader-chunk-${idx}`);
      el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }

  return (
    <Box sx={{ mb: 1.5 }}>
      <Typography sx={{ fontSize: "0.68rem", fontWeight: 600, color: tk.text.muted, mb: 0.75 }}>
        {t("readerBody.sectionTocTitle")}
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
        {sections.map((s) => (
          <Chip
            key={s}
            size="small"
            label={s}
            onClick={() => scrollToSection(s)}
            sx={{
              height: 22,
              fontSize: "0.6875rem",
              maxWidth: "100%",
              borderColor: tk.border.strong,
              "& .MuiChip-label": { overflow: "hidden", textOverflow: "ellipsis" },
            }}
            variant="outlined"
          />
        ))}
      </Box>
    </Box>
  );
}
