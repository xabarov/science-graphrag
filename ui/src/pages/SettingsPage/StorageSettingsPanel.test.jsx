/** @vitest-environment jsdom */
import React from "react";
import { ThemeProvider } from "@mui/material/styles";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../i18n/I18nContext.jsx";
import { buildAppTheme } from "../../theme/buildAppTheme.js";

import StorageSettingsPanel from "./StorageSettingsPanel.jsx";

const theme = buildAppTheme("dark");

afterEach(() => {
  cleanup();
});

function buildStorageSnapshot() {
  return {
    neo4j: {
      fields: {
        neo4j_uri: { effective: "bolt://localhost:7687", source: "environment" },
        neo4j_user: { effective: "neo4j", source: "environment" },
        neo4j_password: { secret_source: "environment", masked: "****" },
      },
    },
    qdrant: {
      fields: {
        qdrant_url: { effective: "http://localhost:6333", source: "environment" },
        qdrant_collection: { effective: "chunks", source: "environment" },
        qdrant_claims_collection: { effective: "claims", source: "environment" },
        qdrant_work_embeddings_collection: { effective: "work_emb", source: "environment" },
        qdrant_author_embeddings_collection: { effective: "author_emb", source: "environment" },
      },
    },
    postgres: {
      fields: {
        database_url: { secret_source: "environment", masked: "postgresql://u:***@h/db" },
      },
    },
    redis: {
      fields: {
        redis_url: { effective: "redis://localhost:6379/0", source: "environment", masked: "redis://localhost:6379/0" },
      },
    },
    paths: {
      fields: {
        blob_root: { effective: "./data/blobs", source: "environment" },
        artifact_root: { effective: "./data/artifacts", source: "environment" },
      },
    },
    s3: {
      fields: {
        object_storage_enabled: { effective: false, source: "environment" },
        s3_endpoint_url: { effective: "", source: "environment" },
        s3_bucket: { effective: "science-raw", source: "environment" },
        s3_use_ssl: { effective: true, source: "environment" },
        s3_addressing_style: { effective: "path", source: "environment" },
        s3_artifact_key_prefix: { effective: "science-artifacts", source: "environment" },
        s3_access_key_id: { effective: "", source: "environment" },
        s3_secret_access_key: { secret_source: "none", masked: null },
        benchmark_runs_object_storage: { effective: false, source: "environment" },
        diagnostics_object_storage: { effective: false, source: "environment" },
        s3_benchmark_runs_key_prefix: { effective: "science-benchmarks", source: "environment" },
        s3_diagnostics_key_prefix: { effective: "science-diagnostics", source: "environment" },
      },
    },
    status: { requires_process_restart: false },
  };
}

describe("StorageSettingsPanel", () => {
  it("submits neo4j_uri when changed", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const onDirty = vi.fn();
    render(
      <ThemeProvider theme={theme}>
        <I18nProvider>
          <StorageSettingsPanel
            storage={buildStorageSnapshot()}
            saving={false}
            saveError=""
            onSave={onSave}
            onDirtyChange={onDirty}
          />
        </I18nProvider>
      </ThemeProvider>,
    );
    const uriInput = screen.getByLabelText(/Bolt/i);
    fireEvent.change(uriInput, { target: { value: "bolt://patched:7687" } });
    fireEvent.click(screen.getByRole("button", { name: /Save storage/i }));
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ neo4j_uri: "bolt://patched:7687" }),
    );
  });
});
