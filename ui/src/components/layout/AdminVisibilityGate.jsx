import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import { Link } from "react-router-dom";

import { CursorPrimaryButton, CursorSmallButton } from "../common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { settingsCardSx } from "../../theme/settingsFormSx.js";

export default function AdminVisibilityGate() {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const cardSx = settingsCardSx(tk);

  return (
    <Box
      sx={{
        maxWidth: 760,
        ...cardSx,
        p: 2,
      }}
    >
      <Typography sx={{ fontWeight: 600, fontSize: "0.9375rem", color: tk.text.primary }}>{t("adminGate.title")}</Typography>
      <Typography sx={{ mt: 1, fontSize: "0.8125rem", color: tk.text.secondary, lineHeight: 1.55 }}>
        {t("adminGate.body")}
      </Typography>
      <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 1 }}>
        <CursorPrimaryButton component={Link} to="/" sx={{ textDecoration: "none" }}>
          {t("adminGate.goHome")}
        </CursorPrimaryButton>
        <CursorSmallButton component={Link} to="/workspaces" sx={{ textDecoration: "none" }}>
          {t("adminGate.workspaces")}
        </CursorSmallButton>
        <CursorSmallButton component={Link} to="/workspace" sx={{ textDecoration: "none" }}>
          {t("adminGate.workspace")}
        </CursorSmallButton>
      </Box>
    </Box>
  );
}
