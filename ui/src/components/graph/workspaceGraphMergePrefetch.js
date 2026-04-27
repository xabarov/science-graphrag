import { expandAggregator } from "../../services/researchApi.js";
import { collectAuthorAggregatorExpandEndpoints } from "./authorSemanticProjection.js";
import { graphTelemetryEmit } from "./graphTelemetry.js";
import { normalizeGraphPayload } from "./graphViewState.js";

/**
 * @param {object | null | undefined} base
 * @param {object | null | undefined} extra
 * @returns {object}
 */
export function mergeWorkspaceRawGraph(base, extra) {
  if (!base || typeof base !== "object") return extra;
  const nmap = new Map();
  for (const n of /** @type {unknown[]} */ (base.nodes || [])) {
    const id = String((n && typeof n === "object" ? n.id : "") || "");
    if (id) nmap.set(id, n);
  }
  for (const n of /** @type {unknown[]} */ (extra.nodes || [])) {
    const id = String((n && typeof n === "object" ? n.id : "") || "");
    if (id) nmap.set(id, n);
  }
  const emap = new Map();
  const ekey = (e) => {
    const o = e && typeof e === "object" ? e : {};
    return o.id || `${o.source}|${o.type}|${o.target}`;
  };
  for (const e of /** @type {unknown[]} */ (base.edges || [])) emap.set(ekey(e), e);
  for (const e of /** @type {unknown[]} */ (extra.edges || [])) emap.set(ekey(e), e);
  return {
    ...base,
    nodes: [...nmap.values()],
    edges: [...emap.values()],
    meta: { ...(typeof base.meta === "object" ? base.meta : {}), ...(typeof extra.meta === "object" ? extra.meta : {}) },
  };
}

/**
 * Prefetch author-related aggregator expansions so the UI can collapse authorship without
 * exposing placeholder Aggregator nodes (workspace + standalone work graphs).
 *
 * @param {object} initialRaw
 * @param {Set<string>} [persistentSeen] when set, endpoints are recorded here to avoid duplicate fetches across calls
 * @returns {Promise<object>}
 */
export async function prefetchAuthorAggregatorExpansions(initialRaw, persistentSeen) {
  let merged = initialRaw;
  const done = persistentSeen ?? new Set();
  for (let round = 0; round < 6; round += 1) {
    const normalized = normalizeGraphPayload(merged);
    const endpoints = collectAuthorAggregatorExpandEndpoints(normalized).filter((ep) => !done.has(ep));
    if (endpoints.length === 0) break;
    graphTelemetryEmit("prefetchAggregatorRound", { round, count: endpoints.length });
    for (const ep of endpoints) {
      done.add(ep);
      try {
        const res = await expandAggregator(ep);
        merged = mergeWorkspaceRawGraph(merged, res.data || {});
      } catch {
        /* keep graph usable if expand fails (e.g. offline); Aggregator may remain until retry */
      }
    }
  }
  return merged;
}
