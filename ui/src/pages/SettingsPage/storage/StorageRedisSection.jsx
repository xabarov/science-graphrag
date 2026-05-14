import React from "react";
import TextField from "@mui/material/TextField";
import { siRedis } from "simple-icons";

import { useI18n } from "../../../i18n/useI18n.js";
import BrandSvgIcon from "../BrandSvgIcon.jsx";
import StorageSectionAccordion from "../StorageSectionAccordion.jsx";

/** @param {Record<string, unknown>} props */
export function StorageRedisSection({ tk, fieldSx, storageAccordionSx, redisUrl, setRedisUrl }) {
  const { t } = useI18n();
  return (
    <StorageSectionAccordion
      defaultExpanded
      accordionSx={storageAccordionSx}
      tk={tk}
      summaryStart={<BrandSvgIcon icon={siRedis} />}
      title={t("settings.storage.redis.title")}
      subtitle={t("settings.storage.redis.subtitle")}
    >
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.redis.url")}
        value={redisUrl}
        onChange={(e) => setRedisUrl(e.target.value)}
        sx={fieldSx}
        size="small"
      />
    </StorageSectionAccordion>
  );
}
