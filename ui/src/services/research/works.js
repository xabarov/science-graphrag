import { apiClient, buildApiUrl } from "../apiClient.js";

/** GET /v1/works */
export async function getWorks({
  q,
  limit = 20,
  offset = 0,
  yearMin,
  yearMax,
  hasSemantic,
} = {}) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (q != null && String(q).trim() !== "") params.set("q", String(q).trim());
  if (yearMin != null && Number.isFinite(Number(yearMin))) params.set("year_min", String(yearMin));
  if (yearMax != null && Number.isFinite(Number(yearMax))) params.set("year_max", String(yearMax));
  if (hasSemantic === true) params.set("has_semantic", "true");
  if (hasSemantic === false) params.set("has_semantic", "false");
  return apiClient.get(buildApiUrl(`/v1/works?${params.toString()}`));
}

/** Absolute URL for GET /v1/works/{work_id}/pdf (for react-pdf ``file`` prop). */
export function workPdfUrl(workId) {
  const id = encodeURIComponent(String(workId ?? "").trim());
  return buildApiUrl(`/v1/works/${id}/pdf`);
}

/** GET /v1/works/{work_id}/sources */
export async function getWorkSources(workId) {
  const id = encodeURIComponent(String(workId ?? "").trim());
  return apiClient.get(buildApiUrl(`/v1/works/${id}/sources`));
}

/** GET /v1/works/{work_id} */
export async function getWorkDetail(workId) {
  const id = encodeURIComponent(String(workId ?? "").trim());
  return apiClient.get(buildApiUrl(`/v1/works/${id}`));
}

/** GET /v1/works/{work_id}/extracted-body — ingest artifact text (not Qdrant chunk join). */
export async function getWorkExtractedBody(workId) {
  const id = encodeURIComponent(String(workId ?? "").trim());
  return apiClient.get(buildApiUrl(`/v1/works/${id}/extracted-body`));
}

/** GET /v1/works/{work_id}/chunks */
export async function getWorkChunks(workId, { limit = 50, offset = 0, section_prefix: sectionPrefix } = {}) {
  const id = encodeURIComponent(String(workId ?? "").trim());
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (sectionPrefix != null && String(sectionPrefix).trim() !== "") {
    params.set("section_prefix", String(sectionPrefix).trim());
  }
  return apiClient.get(buildApiUrl(`/v1/works/${id}/chunks?${params.toString()}`));
}

/** GET /v1/works/{work_id}/claims */
export async function getWorkClaims(workId) {
  const id = encodeURIComponent(String(workId ?? "").trim());
  return apiClient.get(buildApiUrl(`/v1/works/${id}/claims`));
}
