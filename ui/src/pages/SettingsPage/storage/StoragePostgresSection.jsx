import React from "react";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { siPostgresql } from "simple-icons";

import { useI18n } from "../../../i18n/useI18n.js";
import BrandSvgIcon from "../BrandSvgIcon.jsx";
import StorageSectionAccordion from "../StorageSectionAccordion.jsx";

/** @param {Record<string, unknown>} props */
export function StoragePostgresSection({
  tk,
  fieldSx,
  storageAccordionSx,
  storage,
  databaseUrl,
  setDatabaseUrl,
  clearDatabaseUrl,
  setClearDatabaseUrl,
}) {
  const { t } = useI18n();
  return (
    <StorageSectionAccordion
      defaultExpanded
      accordionSx={storageAccordionSx}
      tk={tk}
      summaryStart={<BrandSvgIcon icon={siPostgresql} />}
      title={t("settings.storage.postgres.title")}
      subtitle={t("settings.storage.postgres.subtitle")}
    >
      <TextField
        margin="normal"
        fullWidth
        type="password"
        label={t("settings.storage.postgres.databaseUrl")}
        helperText={storage?.postgres?.fields?.database_url?.masked || ""}
        value={databaseUrl}
        onChange={(e) => setDatabaseUrl(e.target.value)}
        sx={fieldSx}
        size="small"
      />
      <FormControlLabel
        control={
          <Checkbox
            size="small"
            checked={clearDatabaseUrl}
            onChange={(e) => {
              setClearDatabaseUrl(e.target.checked);
              if (e.target.checked) setDatabaseUrl("");
            }}
          />
        }
        label={<Typography sx={{ fontSize: "0.8125rem" }}>{t("settings.storage.secret.clearUseEnv")}</Typography>}
      />
    </StorageSectionAccordion>
  );
}
