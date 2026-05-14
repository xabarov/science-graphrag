import React from "react";
import TextField from "@mui/material/TextField";
import { siQdrant } from "simple-icons";

import { useI18n } from "../../../i18n/useI18n.js";
import BrandSvgIcon from "../BrandSvgIcon.jsx";
import StorageSectionAccordion from "../StorageSectionAccordion.jsx";

/** @param {Record<string, unknown>} props */
export function StorageQdrantSection({
  tk,
  fieldSx,
  storageAccordionSx,
  qdrantUrl,
  setQdrantUrl,
  qdrantCollection,
  setQdrantCollection,
  qdrantClaimsCollection,
  setQdrantClaimsCollection,
  qdrantWorkEmbCollection,
  setQdrantWorkEmbCollection,
  qdrantAuthorEmbCollection,
  setQdrantAuthorEmbCollection,
}) {
  const { t } = useI18n();
  return (
    <StorageSectionAccordion
      defaultExpanded
      accordionSx={storageAccordionSx}
      tk={tk}
      summaryStart={<BrandSvgIcon icon={siQdrant} />}
      title={t("settings.storage.qdrant.title")}
      subtitle={t("settings.storage.qdrant.subtitle")}
    >
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.qdrant.url")}
        value={qdrantUrl}
        onChange={(e) => setQdrantUrl(e.target.value)}
        sx={fieldSx}
        size="small"
      />
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.qdrant.chunks")}
        value={qdrantCollection}
        onChange={(e) => setQdrantCollection(e.target.value)}
        sx={fieldSx}
        size="small"
      />
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.qdrant.claims")}
        value={qdrantClaimsCollection}
        onChange={(e) => setQdrantClaimsCollection(e.target.value)}
        sx={fieldSx}
        size="small"
      />
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.qdrant.workEmb")}
        value={qdrantWorkEmbCollection}
        onChange={(e) => setQdrantWorkEmbCollection(e.target.value)}
        sx={fieldSx}
        size="small"
      />
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.qdrant.authorEmb")}
        value={qdrantAuthorEmbCollection}
        onChange={(e) => setQdrantAuthorEmbCollection(e.target.value)}
        sx={fieldSx}
        size="small"
      />
    </StorageSectionAccordion>
  );
}
