import { useCallback, useEffect, useRef, useState } from "react";

import { expandAggregator, formatResearchApiError, getWorkGraph } from "../../../services/researchApi.js";
import { collectAuthorAggregatorExpandEndpoints } from "../authorSemanticProjection.js";
import {
  getWorkspaceGraph,
  getWorkspaceGraphNeighbors,
  getWorkspaceGraphStats,
} from "../../../utils/workspaceStore.js";
import { normalizeGraphPayload } from "../graphViewState.js";

function mergeWorkspaceRawGraph(base, extra) {
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
async function prefetchAuthorAggregatorExpansions(initialRaw, persistentSeen) {
  let merged = initialRaw;
  const done = persistentSeen ?? new Set();
  for (let round = 0; round < 6; round += 1) {
    const normalized = normalizeGraphPayload(merged);
    const endpoints = collectAuthorAggregatorExpandEndpoints(normalized).filter((ep) => !done.has(ep));
    if (endpoints.length === 0) break;
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

function readWsGraphOptsFromLs(workspaceId, workId = "") {
  const id = String(workspaceId || "").trim();
  const wf = String(workId || "").trim();
  const fallback = {
    mode: "inner_only",
    depth: 1,
    includeExternal: false,
    nodeTypesCsv: "Work,Author",
    externalMinInternalCiters: 0,
    includeClaims: false,
  };
  if (typeof window === "undefined") return fallback;
  try {
    if (id) {
      const modeRaw = window.localStorage.getItem(`workspaceGraphMode:${id}`) || "inner_only";
      const mode = ["inner_only", "union_1hop", "semantic_layer", "full"].includes(modeRaw) ? modeRaw : "inner_only";
      const d = parseInt(window.localStorage.getItem(`workspaceGraphDepth:${id}`) || "1", 10);
      const depth = d === 2 ? 2 : 1;
      const includeExternal = window.localStorage.getItem(`workspaceGraphIncludeExternal:${id}`) === "1";
      const nodeTypesCsv = window.localStorage.getItem(`workspaceGraphNodeTypes:${id}`) || "Work,Author";
      const includeClaims = window.localStorage.getItem(`workspaceGraphIncludeClaims:${id}`) === "1";
      return {
        mode,
        depth,
        includeExternal,
        nodeTypesCsv,
        externalMinInternalCiters: includeExternal ? 2 : 0,
        includeClaims,
      };
    }
    if (wf) {
      const includeClaims = window.localStorage.getItem(`graphWorkIncludeClaims:${wf}`) === "1";
      return { ...fallback, includeClaims };
    }
  } catch {
    return fallback;
  }
  return fallback;
}

export function useGraphWorkspaceData(workspaceId, workId, options = {}) {
  const wsId = String(workspaceId || "").trim();
  const workIdNorm = String(workId || "").trim();
  const [graph, setGraph] = useState(() => normalizeGraphPayload(null));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [wsGraphOpts, setWsGraphOpts] = useState(() => readWsGraphOptsFromLs(wsId, workIdNorm));
  const [wsGraphStats, setWsGraphStats] = useState(null);
  const [workspaceGraphRaw, setWorkspaceGraphRaw] = useState(null);
  const [expandNeighborsBusy, setExpandNeighborsBusy] = useState(false);
  const [neighborCache, setNeighborCache] = useState(() => new Set());
  const authorAggregatorExpandSeenRef = useRef(new Set());

  useEffect(() => {
    setWsGraphOpts(readWsGraphOptsFromLs(wsId, workIdNorm));
    setWorkspaceGraphRaw(null);
    setNeighborCache(new Set());
    authorAggregatorExpandSeenRef.current = new Set();
  }, [wsId, workIdNorm]);

  useEffect(() => {
    if (!wsId) {
      setWsGraphStats(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const stats = await getWorkspaceGraphStats(wsId);
        if (!cancelled) setWsGraphStats(stats);
      } catch {
        if (!cancelled) setWsGraphStats(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [wsId]);

  useEffect(() => {
    const ws = String(workspaceId || "").trim();
    const w = workIdNorm;
    if (!ws && !w) {
      setGraph(normalizeGraphPayload(null));
      setWorkspaceGraphRaw(null);
      setError(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        let normalized;
        if (ws) {
          const raw = await getWorkspaceGraph(ws, {
            neighborLimit: 200,
            mode: wsGraphOpts.mode,
            depth: wsGraphOpts.depth,
            includeExternal: wsGraphOpts.includeExternal,
            nodeTypes: wsGraphOpts.nodeTypesCsv,
            externalMinInternalCiters: wsGraphOpts.externalMinInternalCiters,
            includeClaims: Boolean(wsGraphOpts.includeClaims),
          });
          if (cancelled) return;
          const mergedRaw = await prefetchAuthorAggregatorExpansions(raw, authorAggregatorExpandSeenRef.current);
          if (cancelled) return;
          setWorkspaceGraphRaw(mergedRaw);
          normalized = normalizeGraphPayload(mergedRaw);
        } else {
          setNeighborCache(new Set());
          const depth = options.standaloneWorkGraphDepth === 2 ? 2 : 1;
          const raw = await getWorkGraph(w, {
            depth,
            view: "reader",
            includeClaims: Boolean(wsGraphOpts.includeClaims),
          });
          if (cancelled) return;
          const mergedRaw = await prefetchAuthorAggregatorExpansions(raw.data, authorAggregatorExpandSeenRef.current);
          if (cancelled) return;
          setWorkspaceGraphRaw(mergedRaw);
          normalized = normalizeGraphPayload(mergedRaw);
        }
        if (!cancelled) setGraph(normalized);
      } catch (err) {
        if (cancelled) return;
        setError(formatResearchApiError(err));
        setGraph(normalizeGraphPayload(null));
        setWorkspaceGraphRaw(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workIdNorm, workspaceId, wsGraphOpts, options.standaloneWorkGraphDepth]);

  const fetchNeighbors = useCallback(
    async (nodeId) => {
      const nid = String(nodeId || "").trim();
      if (!wsId || !nid || !workspaceGraphRaw || neighborCache.has(nid)) return;
      setExpandNeighborsBusy(true);
      try {
        const extra = await getWorkspaceGraphNeighbors(wsId, nid, { limit: 80 });
        const merged = mergeWorkspaceRawGraph(workspaceGraphRaw, extra);
        const mergedPrefetched = await prefetchAuthorAggregatorExpansions(merged, authorAggregatorExpandSeenRef.current);
        setWorkspaceGraphRaw(mergedPrefetched);
        setGraph(normalizeGraphPayload(mergedPrefetched));
        setNeighborCache((prev) => new Set([...prev, nid]));
      } catch (err) {
        setError(formatResearchApiError(err));
      } finally {
        setExpandNeighborsBusy(false);
      }
    },
    [wsId, workspaceGraphRaw, neighborCache],
  );

  const expandAggregatorNode = useCallback(
    async (expandEndpoint) => {
      const endpoint = String(expandEndpoint || "").trim();
      if (!endpoint || !workspaceGraphRaw) return;
      authorAggregatorExpandSeenRef.current.add(endpoint);
      setExpandNeighborsBusy(true);
      try {
        const extra = await expandAggregator(endpoint);
        const merged = mergeWorkspaceRawGraph(workspaceGraphRaw, extra.data || {});
        const mergedPrefetched = await prefetchAuthorAggregatorExpansions(merged, authorAggregatorExpandSeenRef.current);
        setWorkspaceGraphRaw(mergedPrefetched);
        setGraph(normalizeGraphPayload(mergedPrefetched));
      } catch (err) {
        setError(formatResearchApiError(err));
      } finally {
        setExpandNeighborsBusy(false);
      }
    },
    [workspaceGraphRaw],
  );

  return {
    wsId,
    graph,
    loading,
    error,
    wsGraphOpts,
    setWsGraphOpts,
    wsGraphStats,
    expandNeighborsBusy,
    fetchNeighbors,
    expandAggregatorNode,
  };
}
