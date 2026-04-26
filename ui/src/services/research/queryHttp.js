import { apiClient, buildApiUrl } from "../apiClient.js";

export function buildQueryBody(query, workId = null, topK = 5, workspaceId = null, mode = "vector") {
  const t = Math.trunc(Number(topK));
  const tk = Number.isFinite(t) ? Math.min(24, Math.max(1, t)) : 5;
  const wid = workId === undefined || workId === "" ? null : workId;
  const ws =
    workspaceId === undefined || workspaceId === null || workspaceId === ""
      ? null
      : String(workspaceId).trim() || null;
  const modeRaw = String(mode || "vector").toLowerCase();
  const m = modeRaw === "hybrid" ? "hybrid" : modeRaw === "agent" ? "agent" : "vector";
  return {
    query: String(query ?? "").trim(),
    work_id: wid,
    workspace_id: ws,
    top_k: tk,
    mode: m,
  };
}

export async function postQuery(body, config) {
  return apiClient.post(buildApiUrl("/v1/query"), body, config);
}
