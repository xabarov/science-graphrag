/**
 * Persist in-flight agent run + UI snapshot for Chat navigation / resume.
 */
const STORAGE_KEY = "science-graphrag:askInflightRun:v1";

function safeSessionStorage() {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

/**
 * @typedef {{
 *   runId: string,
 *   scopeKey: string,
 *   sessionId: string,
 *   workspaceId: string,
 *   pendingUserQuery: string,
 *   lastSeq: number,
 *   streamEvents: unknown[],
 *   agentToolTrace: unknown[],
 *   status: "running" | "completed" | "failed",
 *   updatedAt: string,
 *   composerDraft?: string,
 *   workId?: string,
 * }} AskInflightRunSnapshot
 */

/** @returns {AskInflightRunSnapshot | null} */
export function readInflightRunSnapshot() {
  const storage = safeSessionStorage();
  if (!storage) return null;
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const o = JSON.parse(raw);
    if (!o || typeof o !== "object" || !o.runId) return null;
    return o;
  } catch {
    return null;
  }
}

/** @param {AskInflightRunSnapshot | null} snap */
export function writeInflightRunSnapshot(snap) {
  const storage = safeSessionStorage();
  if (!storage) return;
  try {
    if (!snap || !snap.runId) {
      storage.removeItem(STORAGE_KEY);
      return;
    }
    storage.setItem(STORAGE_KEY, JSON.stringify(snap));
  } catch {
    /* ignore */
  }
}

/** @param {Partial<AskInflightRunSnapshot>} patch */
export function patchInflightRunSnapshot(patch) {
  const prev = readInflightRunSnapshot();
  if (!prev && !patch?.runId) return;
  const next = { ...(prev || {}), ...patch, updatedAt: new Date().toISOString() };
  writeInflightRunSnapshot(/** @type {AskInflightRunSnapshot} */ (next));
}

export function clearInflightRunSnapshot() {
  writeInflightRunSnapshot(null);
}

/**
 * @param {string} scopeKey
 * @param {string} sessionId
 * @returns {boolean}
 */
export function inflightMatchesSession(scopeKey, sessionId) {
  const snap = readInflightRunSnapshot();
  if (!snap || snap.status !== "running") return false;
  return snap.scopeKey === scopeKey && snap.sessionId === sessionId;
}

/**
 * Chat deep link for an in-flight run in the given workspace (drawer return path).
 * @param {string} workspaceId
 * @returns {string}
 */
export function buildInflightChatHref(workspaceId) {
  const snap = readInflightRunSnapshot();
  if (!snap || snap.status !== "running") return "";
  const wid = String(workspaceId || "").trim();
  const snapWid = String(snap.workspaceId || "").trim();
  if (wid && snapWid && wid !== snapWid) return "";
  const sid = String(snap.sessionId || "").trim();
  if (!sid) return "";
  const params = new URLSearchParams();
  if (wid || snapWid) params.set("workspace_id", wid || snapWid);
  params.set("ask_session", sid);
  const workId = String(snap.workId || "").trim();
  if (workId) params.set("work_id", workId);
  return `/chat?${params.toString()}`;
}
