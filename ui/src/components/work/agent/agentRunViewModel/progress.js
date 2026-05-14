import { formatStreamEventOneLine } from "./streamFormat.js";
import { pickLastMeaningfulStreamEvent, pickLastToolCallEvent } from "./streamHeadline.js";

/**
 * Short user-facing line for the run header while streaming (meaningful steps only).
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown[]} streamEvents
 * @param {boolean} isRunActive
 * @returns {string}
 */
export function deriveProgressHint(t, streamEvents, isRunActive) {
  if (!isRunActive) return "";
  const ev = pickLastMeaningfulStreamEvent(streamEvents);
  const line = formatStreamEventOneLine(t, ev);
  if (line) return line;
  const tc = pickLastToolCallEvent(streamEvents);
  if (tc) {
    const toolLine = formatStreamEventOneLine(t, tc);
    if (toolLine) return toolLine;
  }
  return t("chat.run.progressWorking");
}
