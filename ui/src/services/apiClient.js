import axios from "axios";

export const DEFAULT_TIMEOUT_MS = 25_000;

/** Cold Neo4j / Qdrant + work detail often exceed 25s; workspace + work GETs use this. */
export const EXTENDED_READ_TIMEOUT_MS = 90_000;

export function getApiBaseUrl() {
  const v = import.meta.env.VITE_API_BASE_URL;
  if (v == null || String(v).trim() === "") return "";
  return String(v).replace(/\/+$/, "");
}

export function buildApiUrl(path) {
  const base = getApiBaseUrl();
  return base ? `${base}${path}` : path;
}

export const apiClient = axios.create({
  timeout: DEFAULT_TIMEOUT_MS,
});
