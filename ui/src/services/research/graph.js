import { apiClient, buildApiUrl } from "../apiClient.js";

/**
 * GET /v1/works/{work_id}/graph
 * @param {string} workId
 * @param {{
 *   neighborLimit?: number,
 *   depth?: number,
 *   view?: "reader" | "raw",
 *   includeClaims?: boolean,
 *   claimsLimit?: number,
 *   workspaceId?: string | null,
 *   includeInstitutions?: boolean,
 * }} [options]
 */
export async function getWorkGraph(workId, options = {}) {
  const id = encodeURIComponent(String(workId ?? "").trim());
  const params = new URLSearchParams();
  if (options.neighborLimit != null && Number.isFinite(Number(options.neighborLimit))) {
    const lim = Math.min(2000, Math.max(1, Math.floor(Number(options.neighborLimit))));
    params.set("neighbor_limit", String(lim));
  }
  if (options.depth != null && Number.isFinite(Number(options.depth))) {
    const d = Math.min(3, Math.max(1, Math.floor(Number(options.depth))));
    params.set("depth", String(d));
  }
  if (options.prioritize != null && String(options.prioritize).trim()) {
    params.set("prioritize", String(options.prioritize).trim());
  }
  if (options.view && (options.view === "reader" || options.view === "raw")) {
    params.set("view", options.view);
  }
  if (options.includeClaims === true) {
    params.set("include_claims", "true");
  }
  if (options.claimsLimit != null && Number.isFinite(Number(options.claimsLimit))) {
    const v = Math.min(120, Math.max(1, Math.floor(Number(options.claimsLimit))));
    params.set("claims_limit", String(v));
  }
  const ws = options.workspaceId != null ? String(options.workspaceId).trim() : "";
  if (ws) params.set("workspace_id", ws);
  if (options.includeInstitutions === true) {
    params.set("include_institutions", "true");
  }
  const q = params.toString();
  return apiClient.get(buildApiUrl(`/v1/works/${id}/graph${q ? `?${q}` : ""}`));
}

export async function expandAggregator(expandEndpoint) {
  const endpoint = String(expandEndpoint || "").trim();
  if (!endpoint) throw new Error("expand_endpoint_is_required");
  return apiClient.get(buildApiUrl(endpoint));
}
