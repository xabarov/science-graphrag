/** @param {string} workId */
export function workReaderUrl(workId) {
  return `/reader?work_id=${encodeURIComponent(workId)}`;
}

/** @param {string} workId @param {string | null | undefined} workspaceId */
export function workGraphUrl(workId, workspaceId) {
  const p = new URLSearchParams();
  if (workspaceId) p.set("workspace_id", workspaceId);
  if (workId && String(workId).trim()) p.set("work_id", String(workId).trim());
  const qs = p.toString();
  return qs ? `/graph?${qs}` : "/graph";
}

/** @param {string} workId @param {string | null | undefined} workspaceId */
export function workAskUrl(workId, workspaceId) {
  const p = new URLSearchParams();
  if (workId && String(workId).trim()) p.set("work_id", String(workId).trim());
  if (workspaceId && String(workspaceId).trim()) p.set("workspace_id", String(workspaceId).trim());
  const qs = p.toString();
  return qs ? `/ask?${qs}` : "/ask";
}

/** @param {string} workId @param {string | null | undefined} workspaceId */
export function workEvidenceUrl(workId, workspaceId) {
  const p = new URLSearchParams();
  if (workId && String(workId).trim()) p.set("work_id", String(workId).trim());
  if (workspaceId && String(workspaceId).trim()) p.set("workspace_id", String(workspaceId).trim());
  const qs = p.toString();
  return qs ? `/evidence?${qs}` : "/evidence";
}
