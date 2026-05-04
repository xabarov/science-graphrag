const INGEST_JOB_STORAGE_PREFIX = "science-graphrag:workspaceIngestJob:";

export function setPersistedIngestJobId(workspaceId, jobId) {
  const ws = String(workspaceId || "").trim();
  if (!ws) return;
  const key = `${INGEST_JOB_STORAGE_PREFIX}${ws}`;
  try {
    const jid = String(jobId || "").trim();
    if (jid) window.sessionStorage.setItem(key, jid);
    else window.sessionStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

export function readPersistedIngestJobId(workspaceId) {
  const ws = String(workspaceId || "").trim();
  if (!ws) return "";
  try {
    return String(window.sessionStorage.getItem(`${INGEST_JOB_STORAGE_PREFIX}${ws}`) || "").trim();
  } catch {
    return "";
  }
}
