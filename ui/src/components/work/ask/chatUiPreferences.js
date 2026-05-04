const STORAGE_KEY = "science-graphrag-chat-detail-level";

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
