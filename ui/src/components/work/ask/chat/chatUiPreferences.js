const STORAGE_KEY = "science-graphrag-chat-detail-level";
const DETAIL_DISCOVERY_HINT_DISMISSED_KEY = "science-graphrag-chat-detail-discovery-hint-dismissed-v1";

/** @typedef {"simple" | "detailed"} ChatDetailLevel */

/** @returns {ChatDetailLevel} */
export function readChatDetailLevel() {
  try {
    const v = window.localStorage.getItem(STORAGE_KEY);
    return v === "detailed" ? "detailed" : "simple";
  } catch {
    return "simple";
  }
}

/** @param {ChatDetailLevel} level */
export function writeChatDetailLevel(level) {
  const v = level === "detailed" ? "detailed" : "simple";
  try {
    window.localStorage.setItem(STORAGE_KEY, v);
  } catch {
    /* ignore */
  }
}

/** @returns {boolean} */
export function readChatDetailDiscoveryHintDismissed() {
  try {
    return window.localStorage.getItem(DETAIL_DISCOVERY_HINT_DISMISSED_KEY) === "1";
  } catch {
    return false;
  }
}

export function writeChatDetailDiscoveryHintDismissed() {
  try {
    window.localStorage.setItem(DETAIL_DISCOVERY_HINT_DISMISSED_KEY, "1");
  } catch {
    /* ignore */
  }
}
