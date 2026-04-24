import { buildWorkspacePath, getLastWorkId, LAST_WORK_ID_KEY } from "../WorkspacePage/utils/workContext.js";
import { getActiveWorkspaceId } from "../../utils/workspaceStore.js";

export const RECENT_WORKS_KEY = "science-graphrag:recentWorks";

function safeJsonParse(value, fallback) {
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function safeLocalStorage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/**
 * @param {{ workId: string, title?: string, year?: string | number | null, tab?: string, visitedAt?: string, workspaceId?: string | null }} entry
 */
export function rememberRecentWork(entry) {
  const storage = safeLocalStorage();
  if (!storage) return;
  const workId = String(entry?.workId || "").trim();
  if (!workId) return;
  const existing = getRecentWorks();
  const ws =
    entry?.workspaceId != null && String(entry.workspaceId).trim() ? String(entry.workspaceId).trim() : "";
  const nextItem = {
    workId,
    title: entry?.title ? String(entry.title) : "",
    year: entry?.year == null ? null : String(entry.year),
    tab: entry?.tab ? String(entry.tab) : "overview",
    visitedAt: entry?.visitedAt ? String(entry.visitedAt) : new Date().toISOString(),
    workspaceId: ws,
  };
  const deduped = [nextItem, ...existing.filter((item) => item.workId !== workId)].slice(0, 8);
  storage.setItem(RECENT_WORKS_KEY, JSON.stringify(deduped));
}

/**
 * @returns {Array<{workId: string, title: string, year: string | null, tab: string, visitedAt: string, workspaceId: string}>}
 */
export function getRecentWorks() {
  const storage = safeLocalStorage();
  if (!storage) return [];
  const raw = storage.getItem(RECENT_WORKS_KEY);
  if (!raw) return [];
  const parsed = safeJsonParse(raw, []);
  if (!Array.isArray(parsed)) return [];
  return parsed
    .map((item) => ({
      workId: String(item?.workId || "").trim(),
      title: item?.title ? String(item.title) : "",
      year: item?.year == null ? null : String(item.year),
      tab: item?.tab ? String(item.tab) : "overview",
      visitedAt: item?.visitedAt ? String(item.visitedAt) : "",
      workspaceId: item?.workspaceId != null && String(item.workspaceId).trim() ? String(item.workspaceId).trim() : "",
    }))
    .filter((item) => item.workId);
}

/**
 * @returns {{workId: string, path: string} | null}
 */
export function getContinueWorkspaceTarget() {
  const lastWorkId = getLastWorkId();
  if (!lastWorkId) return null;
  const recent = getRecentWorks();
  const match = recent.find((r) => r.workId === lastWorkId);
  const fromRecent = match?.workspaceId ? String(match.workspaceId).trim() : "";
  const fromActive = (() => {
    try {
      return getActiveWorkspaceId() || "";
    } catch {
      return "";
    }
  })();
  const workspaceId = fromRecent || fromActive;
  return {
    workId: lastWorkId,
    path: buildWorkspacePath(lastWorkId, "overview", workspaceId ? { workspaceId } : {}),
  };
}

export function getHomeStatus() {
  const storage = safeLocalStorage();
  const hasLastWork = Boolean(getLastWorkId());
  const hasRecentWorks = getRecentWorks().length > 0;
  return {
    hasLastWork,
    hasRecentWorks,
    hasLocalState: Boolean(storage?.getItem(LAST_WORK_ID_KEY) || storage?.getItem(RECENT_WORKS_KEY)),
  };
}
