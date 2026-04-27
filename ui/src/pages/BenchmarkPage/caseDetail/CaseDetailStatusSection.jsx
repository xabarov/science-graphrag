import React from "react";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../../i18n/useI18n.js";

export default function CaseDetailStatusSection({ error, loading }) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;

  return (
    <>
      {error ? (
        <Typography sx={{ color: tk.state.dangerFg, mb: 1 }} role="alert">
          {error}
        </Typography>
      ) : null}
      {loading ? (
        <Typography sx={{ color: tk.text.secondary }}>{t("benchmark.caseDialog.loading")}</Typography>
      ) : null}
    </>
  );
}
