const PREFIX = "science-graphrag-ask-composer";

/** @param {string} scopeKey */
function storageKey(scopeKey) {
  const sk = String(scopeKey || "default").trim() || "default";
  return `${PREFIX}:${sk}`;
}

/**
 * @param {string} scopeKey
 * @returns {{ webResearchEnabled: boolean, agentMode: "agent" | "plan" }}
 */
export function readAskComposerPrefs(scopeKey) {
  try {
    const raw = window.localStorage.getItem(storageKey(scopeKey));
    if (!raw) return { webResearchEnabled: false, agentMode: "agent" };
    const o = JSON.parse(raw);
    if (!o || typeof o !== "object" || Array.isArray(o)) {
      return { webResearchEnabled: false, agentMode: "agent" };
    }
    const web = Boolean(o.webResearchEnabled);
    const mode = String(o.agentMode || "agent").toLowerCase() === "plan" ? "plan" : "agent";
    return { webResearchEnabled: web, agentMode: mode };
  } catch {
    return { webResearchEnabled: false, agentMode: "agent" };
  }
}

/**
 * @param {string} scopeKey
 * @param {{ webResearchEnabled: boolean, agentMode: "agent" | "plan" }} prefs
 */
export function writeAskComposerPrefs(scopeKey, prefs) {
  try {
    const mode = prefs.agentMode === "plan" ? "plan" : "agent";
    window.localStorage.setItem(
      storageKey(scopeKey),
      JSON.stringify({
        webResearchEnabled: Boolean(prefs.webResearchEnabled),
        agentMode: mode,
      }),
    );
  } catch {
    /* ignore */
  }
}
