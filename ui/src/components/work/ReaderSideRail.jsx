import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../i18n/I18nContext.jsx";

/**
 * Right column: work metadata and RX3 TOC placeholder.
 * @param {{ children?: React.ReactNode }} props
 */
export default function ReaderSideRail({ children = null }) {
  const { t } = useI18n();

  return (
    <Box
      sx={{
        p: 1.5,
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
      }}
    >
      {children}
      <Box sx={{ mt: 2, pt: 2, borderTop: "1px solid rgba(255,255,255,0.08)" }}>
        <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", color: "rgba(255,255,255,0.55)", mb: 0.5 }}>
          {t("readerShell.tocSectionTitle")}
        </Typography>
        <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.38)" }}>{t("readerShell.tocPlaceholder")}</Typography>
      </Box>
    </Box>
  );
}
