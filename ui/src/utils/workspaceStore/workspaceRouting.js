/**
 * Hash-router helpers and last-workspace deep link.
 */

import { getActiveWorkspaceId } from "../activeWorkspacePointer.js";

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
