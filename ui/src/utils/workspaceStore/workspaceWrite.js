/**
 * Workspace mutations (POST/PATCH/DELETE) and dedup decisions.
 */

import { apiClient, apiUrl, httpConfig } from "./workspaceStoreClient.js";

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
