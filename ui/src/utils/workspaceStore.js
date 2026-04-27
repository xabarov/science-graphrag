/**
 * Client helpers for workspace API + active workspace pointer in localStorage.
 */

import {
  apiClient,
  buildApiUrl,
  DEFAULT_TIMEOUT_MS,
  EXTENDED_READ_TIMEOUT_MS,
} from "../services/apiClient.js";
import { formatResearchApiError } from "../services/researchApi.js";

const ACTIVE_WORKSPACE_KEY = "science-graphrag:activeWorkspaceId";

/** Default HTTP timeout so a dead API/Neo4j does not leave the UI stuck on “Loading…”. */
const INGEST_UPLOAD_TIMEOUT_MS = 120_000;
const INGEST_BATCH_TIMEOUT_MS = 600_000;

function httpConfig(extra = {}) {
  return { timeout: DEFAULT_TIMEOUT_MS, ...extra };
}

/** Workspace list/detail/graph/dedup reads hit Neo4j — allow more than default axios 25s. */
function workspaceReadConfig(extra = {}) {
  return { timeout: EXTENDED_READ_TIMEOUT_MS, ...extra };
}

function apiUrl(pathWithQuery) {
  return buildApiUrl(pathWithQuery);
}

/**
 * @returns {string}
 */
export function getActiveWorkspaceId() {
  try {
    const raw = window.localStorage.getItem(ACTIVE_WORKSPACE_KEY);
    return raw && String(raw).trim() ? String(raw).trim() : "";
  } catch {
    return "";
  }
}

/**
 * @param {string} id
 */
export function setActiveWorkspaceId(id) {
  const v = String(id || "").trim();
  try {
    if (!v) window.localStorage.removeItem(ACTIVE_WORKSPACE_KEY);
    else window.localStorage.setItem(ACTIVE_WORKSPACE_KEY, v);
  } catch {
    /* ignore */
  }
}

/**
 * Append or replace `workspace_id` in a hash-router path + query string.
 * @param {string} href e.g. "/graph" or "/graph?work_id=x"
 * @param {string | null | undefined} workspaceId
 * @returns {string}
 */
export function appendWorkspaceQuery(href, workspaceId) {
  const wid = String(workspaceId || "").trim();
  if (!wid) return href;
  const q = href.indexOf("?");
  const path = q >= 0 ? href.slice(0, q) : href;
  const sp = new URLSearchParams(q >= 0 ? href.slice(q + 1) : "");
  sp.set("workspace_id", wid);
  const qs = sp.toString();
  return `${path}?${qs}`;
}

/**
 * Deep link to the last active workspace detail page, or the workspace list.
 * @returns {string}
 */
export function getLastWorkspaceHref() {
  const id = getActiveWorkspaceId();
  return id ? `/workspace?workspace_id=${encodeURIComponent(id)}` : "/workspaces";
}

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
 * @param {string} name
 */
export async function createWorkspace(name) {
  const { data } = await apiClient.post(
    apiUrl("/v1/workspaces"),
    { name: name || "Workspace" },
    httpConfig(),
  );
  return data;
}

export async function renameWorkspace(id, name) {
  const wid = encodeURIComponent(String(id || "").trim());
  const { data } = await apiClient.patch(
    apiUrl(`/v1/workspaces/${wid}`),
    { name: name || "Workspace" },
    httpConfig(),
  );
  return data;
}

export async function deleteWorkspaceApi(id) {
  const wid = encodeURIComponent(String(id || "").trim());
  await apiClient.delete(apiUrl(`/v1/workspaces/${wid}`), httpConfig());
}

export async function addWorkToWorkspace(workspaceId, workId) {
  const wid = encodeURIComponent(String(workspaceId || "").trim());
  const { data } = await apiClient.post(
    apiUrl(`/v1/workspaces/${wid}/works`),
    {
      work_id: String(workId || "").trim(),
    },
    httpConfig(),
  );
  return data;
}

export async function removeWorkFromWorkspace(workspaceId, workId) {
  const ws = encodeURIComponent(String(workspaceId || "").trim());
  const w = encodeURIComponent(String(workId || "").trim());
  const { data } = await apiClient.delete(apiUrl(`/v1/workspaces/${ws}/works/${w}`), httpConfig());
  return data;
}

export async function mergeWorkspacesApi(keepWorkspaceId, dropWorkspaceId) {
  const { data } = await apiClient.post(
    apiUrl("/v1/workspaces/merge"),
    {
      keep_workspace_id: String(keepWorkspaceId || "").trim(),
      drop_workspace_id: String(dropWorkspaceId || "").trim(),
    },
    httpConfig(),
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
 * @param {string} conflictId
 * @param {string | { decision: string, keep_work_id?: string }} decisionOrBody
 */
export async function decideWorkspaceSmartDedupConflict(workspaceId, conflictId, decisionOrBody) {
  const ws = encodeURIComponent(String(workspaceId || "").trim());
  const cid = encodeURIComponent(String(conflictId || "").trim());
  const body =
    typeof decisionOrBody === "string" ? { decision: decisionOrBody } : { ...decisionOrBody };
  const { data } = await apiClient.post(
    apiUrl(`/v1/workspaces/${ws}/dedup/conflicts/${cid}/decide`),
    body,
    httpConfig(),
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
 * @param {string} workspaceId
 * @param {string} conflictId
 * @param {{ decision: string }} body
 */
export async function decideWorkspaceAuthorDedupConflict(workspaceId, conflictId, body) {
  const ws = encodeURIComponent(String(workspaceId || "").trim());
  const cid = encodeURIComponent(String(conflictId || "").trim());
  const { data } = await apiClient.post(
    apiUrl(`/v1/workspaces/${ws}/dedup/authors/conflicts/${cid}/decide`),
    body,
    httpConfig(),
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

/**
 * @param {string} conflictId
 * @param {{ workspaceId?: string, decision: string, keep_entity_id?: string }} body
 */
export async function decideEntityDedupConflict(conflictId, body) {
  const cid = encodeURIComponent(String(conflictId || "").trim());
  const { workspaceId, ...rest } = body || {};
  const params = new URLSearchParams();
  if (workspaceId) params.set("workspace_id", String(workspaceId));
  const q = params.toString();
  const { data } = await apiClient.post(
    apiUrl(`/v1/dedup/entity/${cid}/decide${q ? `?${q}` : ""}`),
    rest,
    httpConfig(),
  );
  return data;
}

