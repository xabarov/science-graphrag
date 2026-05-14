import React from "react";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { siNeo4j } from "simple-icons";

import { useI18n } from "../../../i18n/useI18n.js";
import BrandSvgIcon from "../BrandSvgIcon.jsx";
import StorageSectionAccordion from "../StorageSectionAccordion.jsx";

/** @param {Record<string, unknown>} props */
export function StorageNeo4jSection({
  tk,
  fieldSx,
  storageAccordionSx,
  storage,
  neo4jUri,
  setNeo4jUri,
  neo4jUser,
  setNeo4jUser,
  neo4jPassword,
  setNeo4jPassword,
  clearNeo4jPassword,
  setClearNeo4jPassword,
}) {
  const { t } = useI18n();
  return (
    <StorageSectionAccordion
      defaultExpanded
      accordionSx={storageAccordionSx}
      tk={tk}
      summaryStart={<BrandSvgIcon icon={siNeo4j} />}
      title={t("settings.storage.neo4j.title")}
      subtitle={t("settings.storage.neo4j.subtitle")}
    >
      <Typography sx={{ marginBottom: 1, fontSize: "0.75rem", color: tk.text.muted }}>
        {t("settings.storage.envHint", { keys: "SCIENCE_GRAPHRAG_NEO4J_URI, …" })}
      </Typography>
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.neo4j.uri")}
        value={neo4jUri}
        onChange={(e) => setNeo4jUri(e.target.value)}
        sx={fieldSx}
        size="small"
      />
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.neo4j.user")}
        value={neo4jUser}
        onChange={(e) => setNeo4jUser(e.target.value)}
        sx={fieldSx}
        size="small"
      />
      <TextField
        margin="normal"
        fullWidth
        type="password"
        label={t("settings.storage.neo4j.password")}
        helperText={storage?.neo4j?.fields?.neo4j_password?.masked ? `(${storage.neo4j.fields.neo4j_password.masked})` : ""}
        value={neo4jPassword}
        onChange={(e) => setNeo4jPassword(e.target.value)}
        sx={fieldSx}
        size="small"
      />
      <FormControlLabel
        control={
          <Checkbox
            size="small"
            checked={clearNeo4jPassword}
            onChange={(e) => {
              setClearNeo4jPassword(e.target.checked);
              if (e.target.checked) setNeo4jPassword("");
            }}
          />
        }
        label={<Typography sx={{ fontSize: "0.8125rem" }}>{t("settings.storage.secret.clearUseEnv")}</Typography>}
      />
    </StorageSectionAccordion>
  );
}
