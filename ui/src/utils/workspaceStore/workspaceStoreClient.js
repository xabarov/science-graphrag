/**
 * Shared HTTP client config for workspace API modules.
 */

import {
  apiClient,
  buildApiUrl,
  DEFAULT_TIMEOUT_MS,
  EXTENDED_READ_TIMEOUT_MS,
} from "../../services/apiClient.js";

/** Default HTTP timeout so a dead API/Neo4j does not leave the UI stuck on "Loading…". */
export const INGEST_UPLOAD_TIMEOUT_MS = 120_000;
export const INGEST_BATCH_TIMEOUT_MS = 600_000;

export function httpConfig(extra = {}) {
  return { timeout: DEFAULT_TIMEOUT_MS, ...extra };
}

/** Workspace list/detail/graph/dedup reads hit Neo4j — allow more than default axios 25s. */
export function workspaceReadConfig(extra = {}) {
  return { timeout: EXTENDED_READ_TIMEOUT_MS, ...extra };
}

export function apiUrl(pathWithQuery) {
  return buildApiUrl(pathWithQuery);
}

export { apiClient };
