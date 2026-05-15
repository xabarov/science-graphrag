/**
 * Workspace and graph read endpoints (GET).
 */

import { formatResearchApiError } from "../../services/researchApi.js";
import { apiClient, apiUrl, workspaceReadConfig } from "./workspaceStoreClient.js";

/**
 * @returns {Promise<Array<{ id: string, name: string, created_at?: string, work_ids: string[] }>>}
 */
export async function listWorkspaces() {
  const { data } = await apiClient.get(apiUrl("/v1/workspaces"), workspaceReadConfig());
  const items = Array.isArray(data?.items) ? data.items : [];
  return items;
}

/**
 * @param {string} id
 * @returns {Promise<{ id: string, name: string, created_at?: string, work_ids: string[] } | null>}
 */
export async function getWorkspace(id) {
  const wid = encodeURIComponent(String(id || "").trim());
  if (!wid) return null;
  try {
    const { data } = await apiClient.get(apiUrl(`/v1/workspaces/${wid}`), workspaceReadConfig());
    return data;
  } catch (e) {
    if (e?.response?.status === 404) return null;
    throw new Error(formatResearchApiError(e));
  }
}

/**
 * @param {string} workspaceId
 * @param {string} workIdA
 * @param {string} workIdB
 * @returns {Promise<Record<string, unknown>>}
 */
export async function getWorkspaceContradictionDetail(workspaceId, workIdA, workIdB) {
  const wid = encodeURIComponent(String(workspaceId || "").trim());
  const a = encodeURIComponent(String(workIdA || "").trim());
  const b = encodeURIComponent(String(workIdB || "").trim());
  const params = new URLSearchParams();
  params.set("work_id_a", a);
  params.set("work_id_b", b);
  const q = params.toString();
  const { data } = await apiClient.get(
    apiUrl(`/v1/workspaces/${wid}/graph/contradiction-detail?${q}`),
    workspaceReadConfig(),
  );
  return data;
}

/**
 * @param {string} workspaceId
 * @param {{
 *   mode?: string,
 *   includeExternal?: boolean,
 *   externalMinInternalCiters?: number,
 *   prioritize?: string,
 *   includeClaims?: boolean,
 *   claimsPerWork?: number,
 *   claimsMaxTotal?: number,
 * }} [opts]
 */
export async function getWorkspaceGraph(workspaceId, opts = {}) {
  const wid = encodeURIComponent(String(workspaceId || "").trim());
  const params = new URLSearchParams();
  if (opts.mode != null && String(opts.mode).trim()) {
    params.set("mode", String(opts.mode).trim());
  }
  if (opts.includeExternal === true) {
    params.set("include_external", "true");
  }
  if (opts.externalMinInternalCiters != null && Number.isFinite(Number(opts.externalMinInternalCiters))) {
    const v = Math.min(50, Math.max(0, Math.floor(Number(opts.externalMinInternalCiters))));
    if (v > 0) params.set("external_min_internal_citers", String(v));
  }
  if (opts.prioritize != null && String(opts.prioritize).trim()) {
    params.set("prioritize", String(opts.prioritize).trim());
  }
  if (opts.includeClaims === true) {
    params.set("include_claims", "true");
  }
  if (opts.claimsPerWork != null && Number.isFinite(Number(opts.claimsPerWork))) {
    const v = Math.max(1, Math.floor(Number(opts.claimsPerWork)));
    params.set("claims_per_work", String(v));
  }
  if (opts.claimsMaxTotal != null && Number.isFinite(Number(opts.claimsMaxTotal))) {
    const v = Math.max(1, Math.floor(Number(opts.claimsMaxTotal)));
    params.set("claims_max_total", String(v));
  }
  const q = params.toString();
  const { data } = await apiClient.get(
    apiUrl(`/v1/workspaces/${wid}/graph${q ? `?${q}` : ""}`),
    workspaceReadConfig(),
  );
  return data;
}

/**
 * @param {string} workspaceId
 * @returns {Promise<Record<string, unknown>>}
 */
export async function getWorkspaceGraphStats(workspaceId) {
  const wid = encodeURIComponent(String(workspaceId || "").trim());
  const { data } = await apiClient.get(apiUrl(`/v1/workspaces/${wid}/graph/stats`), workspaceReadConfig());
  return data;
}

/**
 * @param {string} workspaceId
 * @param {string} nodeId
 * @param {{ prioritize?: string }} [opts]
 */
export async function getWorkspaceGraphNeighbors(workspaceId, nodeId, opts = {}) {
  const wid = encodeURIComponent(String(workspaceId || "").trim());
  const params = new URLSearchParams();
  params.set("node_id", String(nodeId || "").trim());
  if (opts.prioritize != null && String(opts.prioritize).trim()) {
    params.set("prioritize", String(opts.prioritize).trim());
  }
  const q = params.toString();
  const { data } = await apiClient.get(
    apiUrl(`/v1/workspaces/${wid}/graph/neighbors?${q}`),
    workspaceReadConfig(),
  );
  return data;
}

/**
 * @param {string} jobId
 * @returns {Promise<Record<string, unknown>>}
 */
export async function getIngestJob(jobId) {
  const id = encodeURIComponent(String(jobId || "").trim());
  const { data } = await apiClient.get(apiUrl(`/v1/ingest/jobs/${id}`), workspaceReadConfig());
  return data;
}

/**
 * @param {string} workspaceId
 * @param {{ status?: string, origin?: string, limit?: number, offset?: number }} [opts]
 */
export async function getWorkspaceSmartDedupConflicts(workspaceId, opts = {}) {
  const wid = encodeURIComponent(String(workspaceId || "").trim());
  const params = new URLSearchParams();
  if (opts.status) params.set("status", String(opts.status));
  if (opts.origin) params.set("origin", String(opts.origin));
  if (opts.limit != null) params.set("limit", String(opts.limit));
  if (opts.offset != null) params.set("offset", String(opts.offset));
  const q = params.toString();
  const { data } = await apiClient.get(
    apiUrl(`/v1/workspaces/${wid}/dedup/conflicts${q ? `?${q}` : ""}`),
    workspaceReadConfig(),
  );
  return data;
}

/**
 * @param {string} workspaceId
 * @param {{ status?: string, origin?: string, limit?: number, offset?: number }} [opts]
 */
export async function getWorkspaceAuthorDedupConflicts(workspaceId, opts = {}) {
  const wid = encodeURIComponent(String(workspaceId || "").trim());
  const params = new URLSearchParams();
  if (opts.status) params.set("status", String(opts.status));
  if (opts.origin) params.set("origin", String(opts.origin));
  if (opts.limit != null) params.set("limit", String(opts.limit));
  if (opts.offset != null) params.set("offset", String(opts.offset));
  const q = params.toString();
  const { data } = await apiClient.get(
    apiUrl(`/v1/workspaces/${wid}/dedup/authors/conflicts${q ? `?${q}` : ""}`),
    workspaceReadConfig(),
  );
  return data;
}

/**
 * @param {{ entityType: string, workspaceId?: string, origin?: string, status?: string, limit?: number, offset?: number }} opts
 */
export async function listEntityDedupConflicts(opts = {}) {
  const params = new URLSearchParams();
  params.set("entity_type", String(opts.entityType || "institution"));
  if (opts.status) params.set("status", String(opts.status));
  if (opts.workspaceId) params.set("workspace_id", String(opts.workspaceId));
  if (opts.origin) params.set("origin", String(opts.origin));
  if (opts.limit != null) params.set("limit", String(opts.limit));
  if (opts.offset != null) params.set("offset", String(opts.offset));
  const { data } = await apiClient.get(
    apiUrl(`/v1/dedup/entity?${params.toString()}`),
    workspaceReadConfig(),
  );
  return data;
}
