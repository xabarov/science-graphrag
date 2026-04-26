import React from "react";
import Typography from "@mui/material/Typography";

import { useI18n } from "../../../i18n/I18nContext.jsx";

export default function CaseDetailStatusSection({ error, loading }) {
  const { t } = useI18n();

  return (
    <>
      {error ? (
        <Typography sx={{ color: "rgba(239, 68, 68, 0.9)", mb: 1 }} role="alert">
          {error}
        </Typography>
      ) : null}
      {loading ? (
        <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>{t("benchmark.caseDialog.loading")}</Typography>
      ) : null}
    </>
  );
}
