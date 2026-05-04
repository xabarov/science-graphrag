import React from "react";
import FolderOutlinedIcon from "@mui/icons-material/FolderOutlined";
import Checkbox from "@mui/material/Checkbox";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { siMinio, siNeo4j, siPostgresql, siQdrant, siRedis } from "simple-icons";

import { useI18n } from "../../i18n/useI18n.js";
import BrandSvgIcon from "./BrandSvgIcon.jsx";
import StorageSectionAccordion from "./StorageSectionAccordion.jsx";

/**
 * All infrastructure accordion sections for storage settings (controlled fields only).
 */
export default function StorageBackendSections({
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
  databaseUrl,
  setDatabaseUrl,
  clearDatabaseUrl,
  setClearDatabaseUrl,
  redisUrl,
  setRedisUrl,
  blobRoot,
  setBlobRoot,
  artifactRoot,
  setArtifactRoot,
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
    <>
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
    </>
  );
}
