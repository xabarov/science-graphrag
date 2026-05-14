import { isHiddenFromSpecialistRunTrace, shouldOmitFromLiveRecentList } from "../agentRunVocabulary.js";
import { collectSafeExplanationLines, deriveDecisionRationale, pickLatestAgentNote } from "./explanations.js";
import { deriveProgressHint } from "./progress.js";
import {
  collectFormattedStreamLines,
  collectRecentToolNamesForChips,
} from "./streamAggregation.js";
import { formatStreamEventOneLine, mapToolNameToUserLabel } from "./streamFormat.js";
import {
  derivePrimaryHeadline,
  pickLastMeaningfulStreamEvent,
  pickLastToolCallEvent,
} from "./streamHeadline.js";

/**
 * @typedef {{
 *   headline: string,
 *   decision: string,
 *   why: string,
 *   latestAgentNote: string,
 *   activityChips: Array<{ tool: string, label: string }>,
 *   explanations: string[],
 *   recentLines: string[],
 *   showRecentToggle: boolean,
 *   showExplainToggle: boolean,
 * }} LiveStatusPresentation
 */

/**
 * After a completed run, suppress the post-run headline when it only repeats
 * the redundant "answer ready" line already implied by the answer section below.
 *
 * @param {unknown[]} streamEvents
 * @returns {boolean}
 */
export function shouldSuppressPostRunStreamSummary(streamEvents) {
  const ev = pickLastMeaningfulStreamEvent(streamEvents);
  if (!ev || typeof ev !== "object") return false;
  return String(/** @type {{ type?: string }} */ (ev).type || "") === "answer_synthesis_finished";
}

/**
 * Single source of truth for the live-run card (headline, chips, explanations, recent list).
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown[]} streamEvents
 * @param {boolean} isRunActive
 * @returns {LiveStatusPresentation}
 */
export function buildLiveStatusPresentation(t, streamEvents, isRunActive) {
  const list = Array.isArray(streamEvents) ? streamEvents : [];
  let headline = derivePrimaryHeadline(t, list, isRunActive);
  if (!headline && !isRunActive) {
    const meaningful = pickLastMeaningfulStreamEvent(list);
    if (meaningful) headline = formatStreamEventOneLine(t, meaningful);
    if (!headline) {
      const tc = pickLastToolCallEvent(list);
      headline = tc ? formatStreamEventOneLine(t, tc) : "";
    }
  }
  const toolNames = isRunActive ? collectRecentToolNamesForChips(list, 4) : [];
  let activityChips = toolNames.map((tool) => ({ tool, label: mapToolNameToUserLabel(t, tool) }));
  if (headline) {
    activityChips = activityChips.filter((chip) => chip.label.trim() !== headline.trim());
  }
  const { decision, why } = deriveDecisionRationale(t, list);
  const latestAgentNote = pickLatestAgentNote(list);
  const explanations = isRunActive
    ? collectSafeExplanationLines(t, list, 6, { excludeKinds: decision || why ? ["decision"] : [] })
    : [];

  const forRecent = list.filter((e) => e && typeof e === "object" && !shouldOmitFromLiveRecentList(e));
  const allLines = collectFormattedStreamLines(t, forRecent, 32);
  const recentLines = headline ? allLines.filter((line) => line !== headline) : allLines;

  const rawCount = list.filter((e) => e && typeof e === "object").length;
  const showRecentToggle = rawCount >= 2 && recentLines.length > 0;
  const showExplainToggle = explanations.length > 0;

  if (!isRunActive && !headline) {
    return {
      headline: "",
      decision: "",
      why: "",
      latestAgentNote: "",
      activityChips: [],
      explanations: [],
      recentLines: [],
      showRecentToggle: false,
      showExplainToggle: false,
    };
  }

  return {
    headline,
    decision,
    why,
    latestAgentNote,
    activityChips,
    explanations,
    recentLines,
    showRecentToggle,
    showExplainToggle,
  };
}

/**
 * Compact header hint while streaming: avoids duplicating the same line as the live card headline.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown[]} streamEvents
 * @param {boolean} isRunActive
 * @returns {string}
 */
export function deriveHeaderProgressHint(t, streamEvents, isRunActive) {
  if (!isRunActive) return "";
  const pres = buildLiveStatusPresentation(t, streamEvents, true);
  const hint = deriveProgressHint(t, streamEvents, true);
  if (pres.headline && hint && pres.headline.trim() === hint.trim()) {
    return t("chat.run.progressWorking");
  }
  if (hint) return hint;
  if (!pres.headline) return t("chat.run.progressWorking");
  return "";
}

/**
 * Group SSE events by specialist_selected boundaries for compact run UI.
 *
 * @param {unknown[]} events
 * @returns {Array<{ key: string, from: string, to: string, isOrphan: boolean, events: unknown[] }>}
 */
export function buildSpecialistStreamGroups(events) {
  if (!Array.isArray(events) || events.length === 0) return [];
  /** @type {Array<{ key: string, from: string, to: string, isOrphan: boolean, events: unknown[] }>} */
  const groups = [];
  /** @type {{ key: string, from: string, to: string, isOrphan: boolean, events: unknown[] } | null} */
  let current = null;
  /** @type {unknown[]} */
  let orphan = [];

  const flushOrphan = () => {
    if (orphan.length === 0) return;
    groups.push({
      key: `orphan-${groups.length}`,
      from: "",
      to: "",
      isOrphan: true,
      events: [...orphan],
    });
    orphan = [];
  };

  for (const ev of events) {
    if (!ev || typeof ev !== "object") continue;
    if (isHiddenFromSpecialistRunTrace(ev)) continue;
    const type = String(ev.type || "");
    if (type === "specialist_selected") {
      flushOrphan();
      const fr = String(ev.from || "");
      const to = String(ev.to || "");
      current = {
        key: `${fr}→${to}-${groups.length}`,
        from: fr,
        to,
        isOrphan: false,
        events: [ev],
      };
      groups.push(current);
      continue;
    }
    if (current) {
      current.events.push(ev);
    } else {
      orphan.push(ev);
    }
  }
  flushOrphan();
  return groups.filter((g) => g.events.length > 0);
}

/**
 * Hide specialist rail when the stream is only low-signal preamble (no routing yet).
 *
 * @param {unknown[]} streamEvents
 * @returns {boolean}
 */
export function shouldShowSubagentRail(streamEvents) {
  const groups = buildSpecialistStreamGroups(streamEvents);
  if (groups.length === 0) return false;
  if (groups.length === 1) {
    const g = groups[0];
    if (g.isOrphan && g.events.length <= 2) return false;
  }
  return true;
}
