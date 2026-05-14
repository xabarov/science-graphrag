import React from "react";

import { StorageNeo4jSection } from "./storage/StorageNeo4jSection.jsx";
import { StoragePathsSection } from "./storage/StoragePathsSection.jsx";
import { StoragePostgresSection } from "./storage/StoragePostgresSection.jsx";
import { StorageQdrantSection } from "./storage/StorageQdrantSection.jsx";
import { StorageRedisSection } from "./storage/StorageRedisSection.jsx";
import { StorageS3Section } from "./storage/StorageS3Section.jsx";

/**
 * All infrastructure accordion sections for storage settings (controlled fields only).
 */
export default function StorageBackendSections(props) {
  const {
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
  } = props;

  return (
    <>
      <StorageS3Section
        tk={tk}
        fieldSx={fieldSx}
        storageAccordionSx={storageAccordionSx}
        storage={storage}
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
      <StorageNeo4jSection
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
      />
      <StorageQdrantSection
        tk={tk}
        fieldSx={fieldSx}
        storageAccordionSx={storageAccordionSx}
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
      />
      <StoragePostgresSection
        tk={tk}
        fieldSx={fieldSx}
        storageAccordionSx={storageAccordionSx}
        storage={storage}
        databaseUrl={databaseUrl}
        setDatabaseUrl={setDatabaseUrl}
        clearDatabaseUrl={clearDatabaseUrl}
        setClearDatabaseUrl={setClearDatabaseUrl}
      />
      <StorageRedisSection
        tk={tk}
        fieldSx={fieldSx}
        storageAccordionSx={storageAccordionSx}
        redisUrl={redisUrl}
        setRedisUrl={setRedisUrl}
      />
      <StoragePathsSection
        tk={tk}
        fieldSx={fieldSx}
        storageAccordionSx={storageAccordionSx}
        blobRoot={blobRoot}
        setBlobRoot={setBlobRoot}
        artifactRoot={artifactRoot}
        setArtifactRoot={setArtifactRoot}
      />
    </>
  );
}
