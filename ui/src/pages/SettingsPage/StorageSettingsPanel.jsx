import React, { useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorPrimaryButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { outlinedAppTextFieldSx, settingsAlertMutedSx, settingsCardSx } from "../../theme/settingsFormSx.js";
import StorageBackendSections from "./StorageBackendSections.jsx";
import { boolEff, strEff } from "./storageSettingsHelpers.js";

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

  const [s3EndpointUrl, setS3EndpointUrl] = useState("");
  const [s3Bucket, setS3Bucket] = useState("");
  const [s3UseSsl, setS3UseSsl] = useState(true);
  const [s3AddressingStyle, setS3AddressingStyle] = useState("path");
  const [s3ArtifactKeyPrefix, setS3ArtifactKeyPrefix] = useState("");
  const [s3AccessKeyId, setS3AccessKeyId] = useState("");
  const [s3SecretAccessKey, setS3SecretAccessKey] = useState("");
  const [clearS3Secret, setClearS3Secret] = useState(false);
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
    setS3EndpointUrl(strEff(storage, "s3.s3_endpoint_url.effective"));
    setS3Bucket(strEff(storage, "s3.s3_bucket.effective"));
    setS3UseSsl(boolEff(storage, "s3.s3_use_ssl.effective"));
    const style = strEff(storage, "s3.s3_addressing_style.effective");
    setS3AddressingStyle(style === "virtual" ? "virtual" : "path");
    setS3ArtifactKeyPrefix(strEff(storage, "s3.s3_artifact_key_prefix.effective"));
    setS3AccessKeyId(strEff(storage, "s3.s3_access_key_id.effective"));
    setS3SecretAccessKey("");
    setClearS3Secret(false);
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
      s3EndpointUrl: strEff(storage, "s3.s3_endpoint_url.effective"),
      s3Bucket: strEff(storage, "s3.s3_bucket.effective"),
      s3UseSsl: boolEff(storage, "s3.s3_use_ssl.effective"),
      s3AddressingStyle: strEff(storage, "s3.s3_addressing_style.effective") === "virtual" ? "virtual" : "path",
      s3ArtifactKeyPrefix: strEff(storage, "s3.s3_artifact_key_prefix.effective"),
      s3AccessKeyId: strEff(storage, "s3.s3_access_key_id.effective"),
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
      s3EndpointUrl !== baseline.s3EndpointUrl ||
      s3Bucket !== baseline.s3Bucket ||
      s3UseSsl !== baseline.s3UseSsl ||
      s3AddressingStyle !== baseline.s3AddressingStyle ||
      s3ArtifactKeyPrefix !== baseline.s3ArtifactKeyPrefix ||
      s3AccessKeyId !== baseline.s3AccessKeyId ||
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
    s3EndpointUrl,
    s3Bucket,
    s3UseSsl,
    s3AddressingStyle,
    s3ArtifactKeyPrefix,
    s3AccessKeyId,
    s3SecretAccessKey,
    clearS3Secret,
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

    if (s3EndpointUrl !== baseline.s3EndpointUrl) payload.s3_endpoint_url = s3EndpointUrl.trim();
    if (s3Bucket !== baseline.s3Bucket) payload.s3_bucket = s3Bucket.trim();
    if (s3UseSsl !== baseline.s3UseSsl) payload.s3_use_ssl = s3UseSsl;
    if (s3AddressingStyle !== baseline.s3AddressingStyle) payload.s3_addressing_style = s3AddressingStyle;
    if (s3ArtifactKeyPrefix !== baseline.s3ArtifactKeyPrefix) payload.s3_artifact_key_prefix = s3ArtifactKeyPrefix.trim();
    if (s3AccessKeyId !== baseline.s3AccessKeyId) payload.s3_access_key_id = s3AccessKeyId.trim();
    if (clearS3Secret) payload.s3_secret_access_key = "";
    else if (s3SecretAccessKey.trim()) payload.s3_secret_access_key = s3SecretAccessKey.trim();

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

      <StorageBackendSections
        tk={tk}
        fieldSx={fieldSx}
        storageAccordionSx={storageAccordionSx}
        storage={storage}
        neo4jUri={neo4jUri}
        setNeo4jUri={setNeo4jUri}
        neo4jUser={neo4jUser}
        setNeo4jUser={setNeo4jUser}
        neo4jPassword={neo4jPassword}
        setNeo4jPassword={setNeo4jPassword}
        clearNeo4jPassword={clearNeo4jPassword}
        setClearNeo4jPassword={setClearNeo4jPassword}
        qdrantUrl={qdrantUrl}
        setQdrantUrl={setQdrantUrl}
        qdrantCollection={qdrantCollection}
        setQdrantCollection={setQdrantCollection}
        qdrantClaimsCollection={qdrantClaimsCollection}
        setQdrantClaimsCollection={setQdrantClaimsCollection}
        qdrantWorkEmbCollection={qdrantWorkEmbCollection}
        setQdrantWorkEmbCollection={setQdrantWorkEmbCollection}
        qdrantAuthorEmbCollection={qdrantAuthorEmbCollection}
        setQdrantAuthorEmbCollection={setQdrantAuthorEmbCollection}
        databaseUrl={databaseUrl}
        setDatabaseUrl={setDatabaseUrl}
        clearDatabaseUrl={clearDatabaseUrl}
        setClearDatabaseUrl={setClearDatabaseUrl}
        redisUrl={redisUrl}
        setRedisUrl={setRedisUrl}
        blobRoot={blobRoot}
        setBlobRoot={setBlobRoot}
        artifactRoot={artifactRoot}
        setArtifactRoot={setArtifactRoot}
        s3EndpointUrl={s3EndpointUrl}
        setS3EndpointUrl={setS3EndpointUrl}
        s3Bucket={s3Bucket}
        setS3Bucket={setS3Bucket}
        s3UseSsl={s3UseSsl}
        setS3UseSsl={setS3UseSsl}
        s3AddressingStyle={s3AddressingStyle}
        setS3AddressingStyle={setS3AddressingStyle}
        s3ArtifactKeyPrefix={s3ArtifactKeyPrefix}
        setS3ArtifactKeyPrefix={setS3ArtifactKeyPrefix}
        s3AccessKeyId={s3AccessKeyId}
        setS3AccessKeyId={setS3AccessKeyId}
        s3SecretAccessKey={s3SecretAccessKey}
        setS3SecretAccessKey={setS3SecretAccessKey}
        clearS3Secret={clearS3Secret}
        setClearS3Secret={setClearS3Secret}
        s3BenchmarkRunsKeyPrefix={s3BenchmarkRunsKeyPrefix}
        setS3BenchmarkRunsKeyPrefix={setS3BenchmarkRunsKeyPrefix}
        s3DiagnosticsKeyPrefix={s3DiagnosticsKeyPrefix}
        setS3DiagnosticsKeyPrefix={setS3DiagnosticsKeyPrefix}
      />

      <Box>
        <CursorPrimaryButton type="submit" disabled={saving || !dirty}>
          {saving ? t("settings.storage.saving") : t("settings.storage.save")}
        </CursorPrimaryButton>
      </Box>
    </Box>
  );
}
