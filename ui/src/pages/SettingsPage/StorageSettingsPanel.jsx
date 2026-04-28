import React, { useEffect, useMemo, useState } from "react";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import FolderOutlinedIcon from "@mui/icons-material/FolderOutlined";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import { siMinio, siNeo4j, siPostgresql, siQdrant, siRedis } from "simple-icons";

import { CursorPrimaryButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { outlinedAppTextFieldSx, settingsAlertMutedSx, settingsCardSx } from "../../theme/settingsFormSx.js";

import BrandSvgIcon from "./BrandSvgIcon.jsx";

function strEff(storage, path) {
  const [a, b, c] = path.split(".");
  try {
    const v = storage?.[a]?.fields?.[b]?.[c];
    if (v === null || v === undefined) return "";
    return String(v).trim();
  } catch {
    return "";
  }
}

function boolEff(storage, path) {
  const [a, b, c] = path.split(".");
  try {
    return Boolean(storage?.[a]?.fields?.[b]?.[c]);
  } catch {
    return false;
  }
}

/**
 * @param {{
 *   defaultExpanded?: boolean;
 *   summaryStart: React.ReactNode;
 *   title: string;
 *   subtitle: string;
 *   accordionSx: object;
 *   tk: import("../../theme/appTokensTypes.js").AppTokens;
 *   children: React.ReactNode;
 * }} props
 */
function StorageSectionAccordion({ defaultExpanded = true, summaryStart, title, subtitle, accordionSx, tk, children }) {
  return (
    <Accordion
      defaultExpanded={defaultExpanded}
      disableGutters
      elevation={0}
      sx={{
        ...accordionSx,
        "&:before": { display: "none" },
        "&.Mui-expanded": { margin: 0 },
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon sx={{ color: tk.text.muted }} />}
        sx={{
          minHeight: 48,
          px: 1.5,
          "& .MuiAccordionSummary-content": {
            alignItems: "center",
            gap: 1.25,
            marginY: 1,
          },
        }}
      >
        <Box sx={{ color: tk.text.secondary, display: "flex", alignItems: "center" }}>{summaryStart}</Box>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.25, minWidth: 0 }}>
          <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>{title}</Typography>
          <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, lineHeight: 1.45 }}>{subtitle}</Typography>
        </Box>
      </AccordionSummary>
      <AccordionDetails sx={{ px: 2, pb: 2, pt: 0, display: "flex", flexDirection: "column" }}>{children}</AccordionDetails>
    </Accordion>
  );
}

export default function StorageSettingsPanel({ storage, saving, saveError, onSave, onDirtyChange }) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const fieldSx = useMemo(() => outlinedAppTextFieldSx(tk), [tk]);
  const cardSx = useMemo(() => settingsCardSx(tk), [tk]);
  const alertMutedSx = useMemo(() => settingsAlertMutedSx(tk), [tk]);
  const storageAccordionSx = useMemo(() => ({ ...cardSx, boxShadow: "none", overflow: "hidden" }), [cardSx]);

  const [neo4jUri, setNeo4jUri] = useState("");
  const [neo4jUser, setNeo4jUser] = useState("");
  const [neo4jPassword, setNeo4jPassword] = useState("");
  const [clearNeo4jPassword, setClearNeo4jPassword] = useState(false);

  const [qdrantUrl, setQdrantUrl] = useState("");
  const [qdrantCollection, setQdrantCollection] = useState("");
  const [qdrantClaimsCollection, setQdrantClaimsCollection] = useState("");
  const [qdrantWorkEmbCollection, setQdrantWorkEmbCollection] = useState("");
  const [qdrantAuthorEmbCollection, setQdrantAuthorEmbCollection] = useState("");

  const [databaseUrl, setDatabaseUrl] = useState("");
  const [clearDatabaseUrl, setClearDatabaseUrl] = useState(false);

  const [redisUrl, setRedisUrl] = useState("");
  const [blobRoot, setBlobRoot] = useState("");
  const [artifactRoot, setArtifactRoot] = useState("");

  const [objectStorageEnabled, setObjectStorageEnabled] = useState(false);
  const [s3EndpointUrl, setS3EndpointUrl] = useState("");
  const [s3Bucket, setS3Bucket] = useState("");
  const [s3UseSsl, setS3UseSsl] = useState(true);
  const [s3AddressingStyle, setS3AddressingStyle] = useState("path");
  const [s3ArtifactKeyPrefix, setS3ArtifactKeyPrefix] = useState("");
  const [s3AccessKeyId, setS3AccessKeyId] = useState("");
  const [s3SecretAccessKey, setS3SecretAccessKey] = useState("");
  const [clearS3Secret, setClearS3Secret] = useState(false);
  const [benchmarkRunsObjectStorage, setBenchmarkRunsObjectStorage] = useState(false);
  const [diagnosticsObjectStorage, setDiagnosticsObjectStorage] = useState(false);
  const [s3BenchmarkRunsKeyPrefix, setS3BenchmarkRunsKeyPrefix] = useState("");
  const [s3DiagnosticsKeyPrefix, setS3DiagnosticsKeyPrefix] = useState("");

  useEffect(() => {
    if (!storage) return;
    /* Sync form fields from server snapshot (same pattern as LlmSettingsPanel). */
    /* eslint-disable react-hooks/set-state-in-effect */
    setNeo4jUri(strEff(storage, "neo4j.neo4j_uri.effective"));
    setNeo4jUser(strEff(storage, "neo4j.neo4j_user.effective"));
    setNeo4jPassword("");
    setClearNeo4jPassword(false);
    setQdrantUrl(strEff(storage, "qdrant.qdrant_url.effective"));
    setQdrantCollection(strEff(storage, "qdrant.qdrant_collection.effective"));
    setQdrantClaimsCollection(strEff(storage, "qdrant.qdrant_claims_collection.effective"));
    setQdrantWorkEmbCollection(strEff(storage, "qdrant.qdrant_work_embeddings_collection.effective"));
    setQdrantAuthorEmbCollection(strEff(storage, "qdrant.qdrant_author_embeddings_collection.effective"));
    setDatabaseUrl("");
    setClearDatabaseUrl(false);
    setRedisUrl(strEff(storage, "redis.redis_url.effective"));
    setBlobRoot(strEff(storage, "paths.blob_root.effective"));
    setArtifactRoot(strEff(storage, "paths.artifact_root.effective"));
    setObjectStorageEnabled(boolEff(storage, "s3.object_storage_enabled.effective"));
    setS3EndpointUrl(strEff(storage, "s3.s3_endpoint_url.effective"));
    setS3Bucket(strEff(storage, "s3.s3_bucket.effective"));
    setS3UseSsl(boolEff(storage, "s3.s3_use_ssl.effective"));
    const style = strEff(storage, "s3.s3_addressing_style.effective");
    setS3AddressingStyle(style === "virtual" ? "virtual" : "path");
    setS3ArtifactKeyPrefix(strEff(storage, "s3.s3_artifact_key_prefix.effective"));
    setS3AccessKeyId(strEff(storage, "s3.s3_access_key_id.effective"));
    setS3SecretAccessKey("");
    setClearS3Secret(false);
    setBenchmarkRunsObjectStorage(boolEff(storage, "s3.benchmark_runs_object_storage.effective"));
    setDiagnosticsObjectStorage(boolEff(storage, "s3.diagnostics_object_storage.effective"));
    setS3BenchmarkRunsKeyPrefix(strEff(storage, "s3.s3_benchmark_runs_key_prefix.effective"));
    setS3DiagnosticsKeyPrefix(strEff(storage, "s3.s3_diagnostics_key_prefix.effective"));
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [storage]);

  const baseline = useMemo(() => {
    if (!storage) return null;
    return {
      neo4jUri: strEff(storage, "neo4j.neo4j_uri.effective"),
      neo4jUser: strEff(storage, "neo4j.neo4j_user.effective"),
      qdrantUrl: strEff(storage, "qdrant.qdrant_url.effective"),
      qdrantCollection: strEff(storage, "qdrant.qdrant_collection.effective"),
      qdrantClaimsCollection: strEff(storage, "qdrant.qdrant_claims_collection.effective"),
      qdrantWorkEmbCollection: strEff(storage, "qdrant.qdrant_work_embeddings_collection.effective"),
      qdrantAuthorEmbCollection: strEff(storage, "qdrant.qdrant_author_embeddings_collection.effective"),
      redisUrl: strEff(storage, "redis.redis_url.effective"),
      blobRoot: strEff(storage, "paths.blob_root.effective"),
      artifactRoot: strEff(storage, "paths.artifact_root.effective"),
      objectStorageEnabled: boolEff(storage, "s3.object_storage_enabled.effective"),
      s3EndpointUrl: strEff(storage, "s3.s3_endpoint_url.effective"),
      s3Bucket: strEff(storage, "s3.s3_bucket.effective"),
      s3UseSsl: boolEff(storage, "s3.s3_use_ssl.effective"),
      s3AddressingStyle: strEff(storage, "s3.s3_addressing_style.effective") === "virtual" ? "virtual" : "path",
      s3ArtifactKeyPrefix: strEff(storage, "s3.s3_artifact_key_prefix.effective"),
      s3AccessKeyId: strEff(storage, "s3.s3_access_key_id.effective"),
      benchmarkRunsObjectStorage: boolEff(storage, "s3.benchmark_runs_object_storage.effective"),
      diagnosticsObjectStorage: boolEff(storage, "s3.diagnostics_object_storage.effective"),
      s3BenchmarkRunsKeyPrefix: strEff(storage, "s3.s3_benchmark_runs_key_prefix.effective"),
      s3DiagnosticsKeyPrefix: strEff(storage, "s3.s3_diagnostics_key_prefix.effective"),
    };
  }, [storage]);

  const dirty = useMemo(() => {
    if (!baseline) return false;
    const scalarDirty =
      neo4jUri !== baseline.neo4jUri ||
      neo4jUser !== baseline.neo4jUser ||
      qdrantUrl !== baseline.qdrantUrl ||
      qdrantCollection !== baseline.qdrantCollection ||
      qdrantClaimsCollection !== baseline.qdrantClaimsCollection ||
      qdrantWorkEmbCollection !== baseline.qdrantWorkEmbCollection ||
      qdrantAuthorEmbCollection !== baseline.qdrantAuthorEmbCollection ||
      redisUrl !== baseline.redisUrl ||
      blobRoot !== baseline.blobRoot ||
      artifactRoot !== baseline.artifactRoot ||
      objectStorageEnabled !== baseline.objectStorageEnabled ||
      s3EndpointUrl !== baseline.s3EndpointUrl ||
      s3Bucket !== baseline.s3Bucket ||
      s3UseSsl !== baseline.s3UseSsl ||
      s3AddressingStyle !== baseline.s3AddressingStyle ||
      s3ArtifactKeyPrefix !== baseline.s3ArtifactKeyPrefix ||
      s3AccessKeyId !== baseline.s3AccessKeyId ||
      benchmarkRunsObjectStorage !== baseline.benchmarkRunsObjectStorage ||
      diagnosticsObjectStorage !== baseline.diagnosticsObjectStorage ||
      s3BenchmarkRunsKeyPrefix !== baseline.s3BenchmarkRunsKeyPrefix ||
      s3DiagnosticsKeyPrefix !== baseline.s3DiagnosticsKeyPrefix;
    const secretDirty =
      Boolean(neo4jPassword.trim()) ||
      clearNeo4jPassword ||
      Boolean(databaseUrl.trim()) ||
      clearDatabaseUrl ||
      Boolean(s3SecretAccessKey.trim()) ||
      clearS3Secret;
    return scalarDirty || secretDirty;
  }, [
    baseline,
    neo4jUri,
    neo4jUser,
    neo4jPassword,
    clearNeo4jPassword,
    qdrantUrl,
    qdrantCollection,
    qdrantClaimsCollection,
    qdrantWorkEmbCollection,
    qdrantAuthorEmbCollection,
    databaseUrl,
    clearDatabaseUrl,
    redisUrl,
    blobRoot,
    artifactRoot,
    objectStorageEnabled,
    s3EndpointUrl,
    s3Bucket,
    s3UseSsl,
    s3AddressingStyle,
    s3ArtifactKeyPrefix,
    s3AccessKeyId,
    s3SecretAccessKey,
    clearS3Secret,
    benchmarkRunsObjectStorage,
    diagnosticsObjectStorage,
    s3BenchmarkRunsKeyPrefix,
    s3DiagnosticsKeyPrefix,
  ]);

  useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!dirty) return;
    const payload = {};
    if (!baseline) return;
    if (neo4jUri !== baseline.neo4jUri) payload.neo4j_uri = neo4jUri.trim();
    if (neo4jUser !== baseline.neo4jUser) payload.neo4j_user = neo4jUser.trim();
    if (clearNeo4jPassword) payload.neo4j_password = "";
    else if (neo4jPassword.trim()) payload.neo4j_password = neo4jPassword.trim();

    if (qdrantUrl !== baseline.qdrantUrl) payload.qdrant_url = qdrantUrl.trim();
    if (qdrantCollection !== baseline.qdrantCollection) payload.qdrant_collection = qdrantCollection.trim();
    if (qdrantClaimsCollection !== baseline.qdrantClaimsCollection)
      payload.qdrant_claims_collection = qdrantClaimsCollection.trim();
    if (qdrantWorkEmbCollection !== baseline.qdrantWorkEmbCollection)
      payload.qdrant_work_embeddings_collection = qdrantWorkEmbCollection.trim();
    if (qdrantAuthorEmbCollection !== baseline.qdrantAuthorEmbCollection)
      payload.qdrant_author_embeddings_collection = qdrantAuthorEmbCollection.trim();

    if (clearDatabaseUrl) payload.database_url = "";
    else if (databaseUrl.trim()) payload.database_url = databaseUrl.trim();

    if (redisUrl !== baseline.redisUrl) payload.redis_url = redisUrl.trim();
    if (blobRoot !== baseline.blobRoot) payload.blob_root = blobRoot.trim();
    if (artifactRoot !== baseline.artifactRoot) payload.artifact_root = artifactRoot.trim();

    if (objectStorageEnabled !== baseline.objectStorageEnabled) payload.object_storage_enabled = objectStorageEnabled;
    if (s3EndpointUrl !== baseline.s3EndpointUrl) payload.s3_endpoint_url = s3EndpointUrl.trim();
    if (s3Bucket !== baseline.s3Bucket) payload.s3_bucket = s3Bucket.trim();
    if (s3UseSsl !== baseline.s3UseSsl) payload.s3_use_ssl = s3UseSsl;
    if (s3AddressingStyle !== baseline.s3AddressingStyle) payload.s3_addressing_style = s3AddressingStyle;
    if (s3ArtifactKeyPrefix !== baseline.s3ArtifactKeyPrefix) payload.s3_artifact_key_prefix = s3ArtifactKeyPrefix.trim();
    if (s3AccessKeyId !== baseline.s3AccessKeyId) payload.s3_access_key_id = s3AccessKeyId.trim();
    if (clearS3Secret) payload.s3_secret_access_key = "";
    else if (s3SecretAccessKey.trim()) payload.s3_secret_access_key = s3SecretAccessKey.trim();

    if (benchmarkRunsObjectStorage !== baseline.benchmarkRunsObjectStorage)
      payload.benchmark_runs_object_storage = benchmarkRunsObjectStorage;
    if (diagnosticsObjectStorage !== baseline.diagnosticsObjectStorage)
      payload.diagnostics_object_storage = diagnosticsObjectStorage;
    if (s3BenchmarkRunsKeyPrefix !== baseline.s3BenchmarkRunsKeyPrefix)
      payload.s3_benchmark_runs_key_prefix = s3BenchmarkRunsKeyPrefix.trim();
    if (s3DiagnosticsKeyPrefix !== baseline.s3DiagnosticsKeyPrefix)
      payload.s3_diagnostics_key_prefix = s3DiagnosticsKeyPrefix.trim();

    await onSave(payload);
  }

  const restartRecommended = Boolean(storage?.status?.requires_process_restart);

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
      <Alert severity="info" sx={alertMutedSx}>
        <Typography sx={{ fontSize: "0.8125rem", lineHeight: 1.6 }}>{t("settings.storage.restartIntro")}</Typography>
      </Alert>
      {restartRecommended ? (
        <Alert severity="warning" sx={alertMutedSx}>
          <Typography sx={{ fontSize: "0.8125rem", lineHeight: 1.6 }}>{t("settings.storage.restartPending")}</Typography>
        </Alert>
      ) : null}
      {saveError ? (
        <Alert severity="error" sx={alertMutedSx}>
          <Typography sx={{ fontSize: "0.8125rem" }}>{saveError}</Typography>
        </Alert>
      ) : null}

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

      <StorageSectionAccordion
        defaultExpanded={false}
        accordionSx={storageAccordionSx}
        tk={tk}
        summaryStart={<BrandSvgIcon icon={siMinio} />}
        title={t("settings.storage.s3.title")}
        subtitle={t("settings.storage.s3.subtitle")}
      >
        <FormControlLabel
          control={<Switch checked={objectStorageEnabled} onChange={(e) => setObjectStorageEnabled(e.target.checked)} />}
          label={<Typography sx={{ fontSize: "0.8125rem" }}>{t("settings.storage.s3.objectStorageEnabled")}</Typography>}
        />
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
        <FormControlLabel
          control={
            <Switch checked={benchmarkRunsObjectStorage} onChange={(e) => setBenchmarkRunsObjectStorage(e.target.checked)} />
          }
          label={
            <Typography sx={{ fontSize: "0.8125rem" }}>{t("settings.storage.s3.benchmarkRunsObjectStorage")}</Typography>
          }
        />
        <FormControlLabel
          control={
            <Switch checked={diagnosticsObjectStorage} onChange={(e) => setDiagnosticsObjectStorage(e.target.checked)} />
          }
          label={<Typography sx={{ fontSize: "0.8125rem" }}>{t("settings.storage.s3.diagnosticsObjectStorage")}</Typography>}
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

      <Box>
        <CursorPrimaryButton type="submit" disabled={saving || !dirty}>
          {saving ? t("settings.storage.saving") : t("settings.storage.save")}
        </CursorPrimaryButton>
      </Box>
    </Box>
  );
}
