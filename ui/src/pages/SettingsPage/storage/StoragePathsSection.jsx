import React from "react";
import FolderOutlinedIcon from "@mui/icons-material/FolderOutlined";
import TextField from "@mui/material/TextField";

import { useI18n } from "../../../i18n/useI18n.js";
import StorageSectionAccordion from "../StorageSectionAccordion.jsx";

/** @param {Record<string, unknown>} props */
export function StoragePathsSection({ tk, fieldSx, storageAccordionSx, blobRoot, setBlobRoot, artifactRoot, setArtifactRoot }) {
  const { t } = useI18n();
  return (
    <StorageSectionAccordion
      defaultExpanded
      accordionSx={storageAccordionSx}
      tk={tk}
      summaryStart={<FolderOutlinedIcon sx={{ fontSize: 22 }} />}
      title={t("settings.storage.paths.title")}
      subtitle={t("settings.storage.paths.subtitle")}
    >
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.paths.blobRoot")}
        value={blobRoot}
        onChange={(e) => setBlobRoot(e.target.value)}
        sx={fieldSx}
        size="small"
      />
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.paths.artifactRoot")}
        value={artifactRoot}
        onChange={(e) => setArtifactRoot(e.target.value)}
        sx={fieldSx}
        size="small"
      />
    </StorageSectionAccordion>
  );
}
