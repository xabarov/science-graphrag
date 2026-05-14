import { formatStreamEventOneLine } from "./streamFormat.js";

/**
 * Stable group key for aggregation: events with the same key fold into one
 * "(×N)" line when adjacent. Returns empty string when an event must not be
 * aggregated.
 *
 * @param {unknown} event
 * @returns {string}
 */
export function getEventGroupKey(event) {
  if (!event || typeof event !== "object") return "";
  const ev = /** @type {Record<string, unknown>} */ (event);
  const type = String(ev.type || "");
  if (type === "tool_call") {
    const tool = String(ev.tool || "").trim();
    return tool ? `tool_call:${tool}` : "";
  }
  if (type === "product_step") {
    const code = String(ev.code || "").trim();
    if (!code) return "";
    if (code === "using_tool") {
      const tool = String(ev.tool || "").trim();
      return tool ? `product_step:using_tool:${tool}` : "product_step:using_tool";
    }
    return `product_step:${code}`;
  }
  return "";
}

/**
 * @typedef {{
 *   kind: "single" | "group",
 *   event: Record<string, unknown>,
 *   count: number,
 *   firstIdx: number,
 *   lastIdx: number,
 * }} AggregatedEvent
 */

/**
 * Collapse adjacent repeats of the same `tool_call` / `product_step` into a
 * single virtual event with `count`. Non-aggregatable events pass through as
 * `{ kind: "single", count: 1 }`. The order of underlying events is preserved.
 *
 * @param {unknown[]} events
 * @returns {AggregatedEvent[]}
 */
export function aggregateRepeatedEvents(events) {
  if (!Array.isArray(events) || events.length === 0) return [];
  /** @type {AggregatedEvent[]} */
  const out = [];
  for (let i = 0; i < events.length; i += 1) {
    const ev = events[i];
    if (!ev || typeof ev !== "object") continue;
    const obj = /** @type {Record<string, unknown>} */ (ev);
    const key = getEventGroupKey(obj);
    if (!key) {
      out.push({ kind: "single", event: obj, count: 1, firstIdx: i, lastIdx: i });
      continue;
    }
    const last = out.length > 0 ? out[out.length - 1] : null;
    if (last && getEventGroupKey(last.event) === key) {
      last.kind = "group";
      last.count += 1;
      last.lastIdx = i;
      continue;
    }
    out.push({ kind: "single", event: obj, count: 1, firstIdx: i, lastIdx: i });
  }
  return out;
}

/**
 * Format an aggregated entry. Single entries delegate to
 * `formatStreamEventOneLine`; groups append `(×N)` via the
 * `chat.run.headline.repeatedSuffix` template.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {AggregatedEvent} entry
 * @returns {string}
 */
export function formatAggregatedEventOneLine(t, entry) {
  if (!entry || typeof entry !== "object") return "";
  const base = formatStreamEventOneLine(t, entry.event);
  if (!base) return "";
  if (entry.count <= 1) return base;
  const ev = /** @type {Record<string, unknown>} */ (entry.event);
  const type = ev && typeof ev === "object" ? String(ev.type || "") : "";
  const key =
    type === "tool_call"
      ? "chat.run.live.toolCallRepeated"
      : type === "product_step"
        ? "chat.run.live.productStepRepeated"
        : "chat.run.headline.repeatedSuffix";
  const vars = { base, count: String(entry.count) };
  const out = t(key, vars);
  return out === key ? t("chat.run.headline.repeatedSuffix", vars) : out;
}

/**
 * One formatted line per event (chronological), for expandable live status.
 * Adjacent repeats of `tool_call` / `product_step` are collapsed into a single
 * "(×N)" line so long bursts do not flood the recent list.
 *
 * @param {(key: string, vars?: Record<string, string>) => string} t
 * @param {unknown[]} events
 * @param {number} [limit]
 * @returns {string[]}
 */
export function collectFormattedStreamLines(t, events, limit = 24) {
  if (!Array.isArray(events) || events.length === 0) return [];
  const aggregated = aggregateRepeatedEvents(events);
  const lines = [];
  for (const entry of aggregated) {
    const line = formatAggregatedEventOneLine(t, entry);
    if (line) lines.push(line);
  }
  if (lines.length <= limit) return lines;
  return lines.slice(-limit);
}

/**
 * @param {unknown[]} events
 * @param {number} [maxChips]
 * @returns {string[]}
 */
export function collectRecentToolNamesForChips(events, maxChips = 4) {
  if (!Array.isArray(events) || events.length === 0) return [];
  /** @type {string[]} */
  const ordered = [];
  for (const ev of events) {
    if (!ev || typeof ev !== "object") continue;
    if (String(ev.type || "") !== "tool_call") continue;
    const name = String(ev.tool || "").trim();
    if (!name) continue;
    const normalized = name.toLowerCase().replace(/-/g, "_");
    if (normalized === "final_answer") continue;
    ordered.push(name);
  }
  if (ordered.length === 0) return [];
  const tail = ordered.slice(-12);
  /** @type {string[]} */
  const out = [];
  for (let i = tail.length - 1; i >= 0 && out.length < maxChips; i -= 1) {
    const n = tail[i];
    if (!out.includes(n)) out.push(n);
  }
  return out;
}
