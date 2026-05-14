/**
 * Scope keys and migration policies for Ask session bundles (no turn CRUD).
 */

import { translate } from "../../../../i18n/translate.js";
import { readStoredLocale } from "../../../../i18n/readStoredLocale.js";
import { getAskHistory } from "./askHistoryState.js";
import { newSessionId, normalizeTurn } from "./askSessionModel.js";
import { ASK_SESSION_MAX_TURNS } from "./askSessionConstants.js";
import { getBundle, isAskSessionStorageAvailable, saveBundle } from "./askSessionStorage.js";

export function deriveAskScopeKey({ locked, scopedWorkId, workspaceId }) {
  const wid = String(scopedWorkId || "").trim();
  if (locked && wid) {
    return `workspace:${wid}`;
  }
  const ws = String(workspaceId || "").trim();
  if (ws) {
    return `standalone-ws:${ws}`;
  }
  return "standalone";
}

/**
 * When `workspaceId` appears after the user already chatted under `standalone`,
 * copy the local bundle to `standalone-ws:<id>` so the thread does not look empty.
 * No-op if the target scope already has at least one stored turn.
 *
 * @param {string} workspaceId
 */
export function maybeMigrateStandaloneBundleToWorkspaceScope(workspaceId) {
  if (!isAskSessionStorageAvailable()) return;
  const wid = String(workspaceId || "").trim();
  if (!wid) return;
  const fromKey = "standalone";
  const toKey = `standalone-ws:${wid}`;
  if (fromKey === toKey) return;
  const toBundle = getBundle(toKey);
  const toHasTurns = toBundle.sessions.some((s) => (s.entries || []).length > 0);
  if (toHasTurns) return;
  const fromBundle = getBundle(fromKey);
  const fromHasTurns = fromBundle.sessions.some((s) => (s.entries || []).length > 0);
  if (!fromHasTurns) return;
  saveBundle(toKey, {
    activeId: fromBundle.activeId,
    sessions: fromBundle.sessions.map((s) => ({
      ...s,
      entries: [...(s.entries || [])],
    })),
  });
}

/**
 * One-time import from flat ask history when this scope has no sessions yet.
 *
 * @param {string} scopeKey
 * @param {(item: { workId: string }) => boolean} filterLegacyItem
 */
export function migrateLegacyAskHistoryToSessions(scopeKey, filterLegacyItem) {
  if (!isAskSessionStorageAvailable()) return;
  const bundle = getBundle(scopeKey);
  if (bundle.sessions.length > 0) return;
  const legacy = getAskHistory().filter(filterLegacyItem);
  if (legacy.length === 0) return;
  const id = newSessionId();
  const entries = legacy.slice(0, ASK_SESSION_MAX_TURNS).map((item) => normalizeTurn(item));
  const now = new Date().toISOString();
  saveBundle(scopeKey, {
    activeId: id,
    sessions: [
      {
        id,
        title: translate("ask.session.imported", readStoredLocale()),
        updatedAt: now,
        entries,
      },
    ],
  });
}
