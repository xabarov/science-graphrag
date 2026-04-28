import {
  defaultGraphVisibility,
  normalizeGraphVisibilityValue,
} from "./graphVisibilityFilter.js";

/** @param {string} workspaceId @param {string} workId */
export function graphVisibilityLocalStorageKey(workspaceId = "", workId = "") {
  const wid = String(workspaceId || "").trim();
  const wf = String(workId || "").trim();
  if (wid) return `workspaceGraphVisibility:v1:${wid}`;
  if (wf) return `graphWorkVisibility:v1:${wf}`;
  return "graphVisibility:v1:";
}

/**
 * @param {string} workspaceId
 * @param {string} workId
 */
export function readGraphVisibilityFromLs(workspaceId, workId = "") {
  const wid = String(workspaceId || "").trim();
  const wf = String(workId || "").trim();
  const def = defaultGraphVisibility();
  if (typeof window === "undefined") return def;
  try {
    const key = graphVisibilityLocalStorageKey(wid, wf);
    const raw = window.localStorage.getItem(key);
    if (raw && String(raw).trim()) {
      return normalizeGraphVisibilityValue(JSON.parse(raw));
    }
    if (wid) {
      const nodeTypesCsv = window.localStorage.getItem(`workspaceGraphNodeTypes:${wid}`) || "";
      const parts = nodeTypesCsv
        .split(/[,;]/)
        .map((s) => s.trim())
        .filter(Boolean);
      const showExternalWorks = window.localStorage.getItem(`workspaceGraphIncludeExternal:${wid}`) === "1";
      const showClaims = window.localStorage.getItem(`workspaceGraphIncludeClaims:${wid}`) === "1";
      if (parts.length) {
        return normalizeGraphVisibilityValue({
          types: parts,
          showExternalWorks,
          showClaims,
        });
      }
      return normalizeGraphVisibilityValue({ ...def, showExternalWorks, showClaims });
    }
    if (wf) {
      const showClaims = window.localStorage.getItem(`graphWorkIncludeClaims:${wf}`) === "1";
      return normalizeGraphVisibilityValue({ ...def, showClaims });
    }
  } catch {
    return def;
  }
  return def;
}

/**
 * @param {string} workspaceId
 * @param {string} workId
 * @param {import("./graphVisibilityFilter.js").GraphVisibilityValue} value
 */
export function writeGraphVisibilityToLs(workspaceId, workId, value) {
  if (typeof window === "undefined") return;
  try {
    const key = graphVisibilityLocalStorageKey(workspaceId, workId);
    if (!key || key === "graphVisibility:v1:") return;
    window.localStorage.setItem(key, JSON.stringify(normalizeGraphVisibilityValue(value)));
  } catch {
    /* ignore */
  }
}
