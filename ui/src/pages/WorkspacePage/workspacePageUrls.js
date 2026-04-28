import { buildStandaloneChatPath, buildStandaloneTracePath } from "../../routing/index.js";
import { GRAPH_PATH, READER_PATH } from "../../routes/paths.js";

function trimWorkId(workId) {
  return workId && String(workId).trim() ? String(workId).trim() : "";
}

function trimWorkspaceId(workspaceId) {
  return workspaceId && String(workspaceId).trim() ? String(workspaceId).trim() : "";
}

/** @param {string} workId */
export function workReaderUrl(workId) {
  return buildStandaloneTracePath(READER_PATH, trimWorkId(workId), {});
}

/** @param {string} workId @param {string | null | undefined} workspaceId */
export function workGraphUrl(workId, workspaceId) {
  const wid = trimWorkId(workId);
  const ws = trimWorkspaceId(workspaceId);
  return buildStandaloneTracePath(GRAPH_PATH, wid, ws ? { workspaceId: ws } : {});
}

/** @param {string} workId @param {string | null | undefined} workspaceId */
export function workChatUrl(workId, workspaceId) {
  const wid = trimWorkId(workId);
  const ws = trimWorkspaceId(workspaceId);
  return buildStandaloneChatPath(wid, ws ? { workspaceId: ws } : {});
}

/** @deprecated Use {@link workChatUrl}; kept for incremental refactors. */
export function workAskUrl(workId, workspaceId) {
  return workChatUrl(workId, workspaceId);
}
