/**
 * Client helpers for workspace API + active workspace pointer in localStorage.
 */

import axios from "axios";

import { formatResearchApiError, getResearchApiBaseUrl } from "../services/researchApi.js";

const ACTIVE_WORKSPACE_KEY = "science-graphrag:activeWorkspaceId";

function apiUrl(pathWithQuery) {
  const base = getResearchApiBaseUrl();
  return base ? `${base}${pathWithQuery}` : pathWithQuery;
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
 * @returns {Promise<Array<{ id: string, name: string, created_at?: string, work_ids: string[] }>>}
 */
export async function listWorkspaces() {
  const { data } = await axios.get(apiUrl("/v1/workspaces"));
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
    const { data } = await axios.get(apiUrl(`/v1/workspaces/${wid}`));
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
  const { data } = await axios.post(apiUrl("/v1/workspaces"), { name: name || "Workspace" });
  return data;
}

export async function renameWorkspace(id, name) {
  const wid = encodeURIComponent(String(id || "").trim());
  const { data } = await axios.patch(apiUrl(`/v1/workspaces/${wid}`), { name: name || "Workspace" });
  return data;
}

export async function deleteWorkspaceApi(id) {
  const wid = encodeURIComponent(String(id || "").trim());
  await axios.delete(apiUrl(`/v1/workspaces/${wid}`));
}

export async function addWorkToWorkspace(workspaceId, workId) {
  const wid = encodeURIComponent(String(workspaceId || "").trim());
  const { data } = await axios.post(apiUrl(`/v1/workspaces/${wid}/works`), {
    work_id: String(workId || "").trim(),
  });
  return data;
}

export async function removeWorkFromWorkspace(workspaceId, workId) {
  const ws = encodeURIComponent(String(workspaceId || "").trim());
  const w = encodeURIComponent(String(workId || "").trim());
  const { data } = await axios.delete(apiUrl(`/v1/workspaces/${ws}/works/${w}`));
  return data;
}

export async function mergeWorkspacesApi(keepWorkspaceId, dropWorkspaceId) {
  const { data } = await axios.post(apiUrl("/v1/workspaces/merge"), {
    keep_workspace_id: String(keepWorkspaceId || "").trim(),
    drop_workspace_id: String(dropWorkspaceId || "").trim(),
  });
  return data;
}

/**
 * @param {string} workspaceId
 * @param {{ neighborLimit?: number }} [opts]
 */
export async function getWorkspaceGraph(workspaceId, opts = {}) {
  const wid = encodeURIComponent(String(workspaceId || "").trim());
  const params = new URLSearchParams();
  if (opts.neighborLimit != null && Number.isFinite(Number(opts.neighborLimit))) {
    params.set("neighbor_limit", String(Math.min(2000, Math.max(1, Math.floor(Number(opts.neighborLimit))))));
  }
  const q = params.toString();
  const { data } = await axios.get(apiUrl(`/v1/workspaces/${wid}/graph${q ? `?${q}` : ""}`));
  return data;
}

export async function getWorkspaceDedupCandidates(workspaceId) {
  const wid = encodeURIComponent(String(workspaceId || "").trim());
  const { data } = await axios.get(apiUrl(`/v1/workspaces/${wid}/deduplication-candidates`));
  return Array.isArray(data?.items) ? data.items : [];
}

export async function mergeWorksInWorkspace(workspaceId, keepWorkId, dropWorkId) {
  const wid = encodeURIComponent(String(workspaceId || "").trim());
  const { data } = await axios.post(apiUrl(`/v1/workspaces/${wid}/merge-works`), {
    keep_work_id: String(keepWorkId || "").trim(),
    drop_work_id: String(dropWorkId || "").trim(),
  });
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
  const { data } = await axios.post(apiUrl(`/v1/workspaces/${wid}/ingest/document`), form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

/**
 * @param {string} jobId
 * @returns {Promise<Record<string, unknown>>}
 */
export async function getIngestJob(jobId) {
  const id = encodeURIComponent(String(jobId || "").trim());
  const { data } = await axios.get(apiUrl(`/v1/ingest/jobs/${id}`));
  return data;
}
