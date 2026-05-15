/**
 * Workspace document ingest uploads (multipart).
 */

import { apiClient, apiUrl, INGEST_BATCH_TIMEOUT_MS, INGEST_UPLOAD_TIMEOUT_MS } from "./workspaceStoreClient.js";

/**
 * Upload PDF / Markdown / plain text into a workspace; returns initial job payload (poll {@link getIngestJob}).
 * @param {string} workspaceId
 * @param {File} file
 * @returns {Promise<Record<string, unknown>>}
 */
export async function startWorkspaceDocumentIngest(workspaceId, file) {
  const wid = encodeURIComponent(String(workspaceId || "").trim());
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post(apiUrl(`/v1/workspaces/${wid}/ingest/document`), form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: INGEST_UPLOAD_TIMEOUT_MS,
  });
  return data;
}

/**
 * Batch upload: multiple files and/or a ``.zip`` of PDF/MD/TXT (poll parent job id).
 * @param {string} workspaceId
 * @param {File[]} files
 * @param {File | null} [archive]
 */
export async function startWorkspaceBatchIngest(workspaceId, files, archive = null) {
  const wid = encodeURIComponent(String(workspaceId || "").trim());
  const form = new FormData();
  if (Array.isArray(files)) {
    for (const f of files) {
      if (f) form.append("files", f);
    }
  }
  if (archive) {
    form.append("archive", archive);
  }
  const { data } = await apiClient.post(apiUrl(`/v1/workspaces/${wid}/ingest/batch`), form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: INGEST_BATCH_TIMEOUT_MS,
  });
  return data;
}
