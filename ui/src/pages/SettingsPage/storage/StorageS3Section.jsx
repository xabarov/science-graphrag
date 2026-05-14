import React from "react";
import Checkbox from "@mui/material/Checkbox";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { siMinio } from "simple-icons";

import { useI18n } from "../../../i18n/useI18n.js";
import BrandSvgIcon from "../BrandSvgIcon.jsx";
import StorageSectionAccordion from "../StorageSectionAccordion.jsx";

/** @param {Record<string, unknown>} props */
export function StorageS3Section({
  tk,
  fieldSx,
  storageAccordionSx,
  storage,
  s3EndpointUrl,
  setS3EndpointUrl,
  s3Bucket,
  setS3Bucket,
  s3UseSsl,
  setS3UseSsl,
  s3AddressingStyle,
  setS3AddressingStyle,
  s3ArtifactKeyPrefix,
  setS3ArtifactKeyPrefix,
  s3AccessKeyId,
  setS3AccessKeyId,
  s3SecretAccessKey,
  setS3SecretAccessKey,
  clearS3Secret,
  setClearS3Secret,
  s3BenchmarkRunsKeyPrefix,
  setS3BenchmarkRunsKeyPrefix,
  s3DiagnosticsKeyPrefix,
  setS3DiagnosticsKeyPrefix,
}) {
  const { t } = useI18n();
  return (
    <StorageSectionAccordion
      defaultExpanded
      accordionSx={storageAccordionSx}
      tk={tk}
      summaryStart={<BrandSvgIcon icon={siMinio} />}
      title={t("settings.storage.s3.title")}
      subtitle={t("settings.storage.s3.subtitle")}
    >
      <Typography sx={{ marginBottom: 1, fontSize: "0.75rem", color: tk.text.muted }}>
        {t("settings.storage.s3.envHint", {
          keys: "SCIENCE_GRAPHRAG_S3_ENDPOINT_URL, SCIENCE_GRAPHRAG_S3_ACCESS_KEY_ID, SCIENCE_GRAPHRAG_S3_SECRET_ACCESS_KEY, SCIENCE_GRAPHRAG_S3_BUCKET, …",
        })}
      </Typography>
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.s3.endpoint")}
        value={s3EndpointUrl}
        onChange={(e) => setS3EndpointUrl(e.target.value)}
        sx={fieldSx}
        size="small"
      />
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.s3.bucket")}
        value={s3Bucket}
        onChange={(e) => setS3Bucket(e.target.value)}
        sx={fieldSx}
        size="small"
      />
      <FormControlLabel
        control={<Switch checked={s3UseSsl} onChange={(e) => setS3UseSsl(e.target.checked)} />}
        label={<Typography sx={{ fontSize: "0.8125rem" }}>{t("settings.storage.s3.useSsl")}</Typography>}
      />
      <FormControl margin="normal" fullWidth size="small" sx={fieldSx}>
        <InputLabel id="s3-addressing-style">{t("settings.storage.s3.addressingStyle")}</InputLabel>
        <Select
          labelId="s3-addressing-style"
          label={t("settings.storage.s3.addressingStyle")}
          value={s3AddressingStyle}
          onChange={(e) => setS3AddressingStyle(e.target.value)}
        >
          <MenuItem value="path">path</MenuItem>
          <MenuItem value="virtual">virtual</MenuItem>
        </Select>
      </FormControl>
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.s3.artifactPrefix")}
        value={s3ArtifactKeyPrefix}
        onChange={(e) => setS3ArtifactKeyPrefix(e.target.value)}
        sx={fieldSx}
        size="small"
      />
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.s3.accessKeyId")}
        value={s3AccessKeyId}
        onChange={(e) => setS3AccessKeyId(e.target.value)}
        sx={fieldSx}
        size="small"
      />
      <TextField
        margin="normal"
        fullWidth
        type="password"
        label={t("settings.storage.s3.secretKey")}
        helperText={storage?.s3?.fields?.s3_secret_access_key?.masked || ""}
        value={s3SecretAccessKey}
        onChange={(e) => setS3SecretAccessKey(e.target.value)}
        sx={fieldSx}
        size="small"
      />
      <FormControlLabel
        control={
          <Checkbox
            size="small"
            checked={clearS3Secret}
            onChange={(e) => {
              setClearS3Secret(e.target.checked);
              if (e.target.checked) setS3SecretAccessKey("");
            }}
          />
        }
        label={<Typography sx={{ fontSize: "0.8125rem" }}>{t("settings.storage.secret.clearUseEnv")}</Typography>}
      />
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.s3.benchmarkPrefix")}
        value={s3BenchmarkRunsKeyPrefix}
        onChange={(e) => setS3BenchmarkRunsKeyPrefix(e.target.value)}
        sx={fieldSx}
        size="small"
      />
      <TextField
        margin="normal"
        fullWidth
        label={t("settings.storage.s3.diagnosticsPrefix")}
        value={s3DiagnosticsKeyPrefix}
        onChange={(e) => setS3DiagnosticsKeyPrefix(e.target.value)}
        sx={fieldSx}
        size="small"
      />
    </StorageSectionAccordion>
  );
}
