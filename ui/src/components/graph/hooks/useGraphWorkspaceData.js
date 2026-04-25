import { useCallback, useEffect, useState } from "react";

import { expandAggregator, formatResearchApiError, getWorkGraph } from "../../../services/researchApi.js";
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

function readWsGraphOptsFromLs(workspaceId) {
  const id = String(workspaceId || "").trim();
  const fallback = {
    mode: "inner_only",
    depth: 1,
    includeExternal: false,
    nodeTypesCsv: "Work,Author",
    externalMinInternalCiters: 0,
  };
  if (!id || typeof window === "undefined") return fallback;
  try {
    const modeRaw = window.localStorage.getItem(`workspaceGraphMode:${id}`) || "inner_only";
    const mode = ["inner_only", "union_1hop", "semantic_layer", "full"].includes(modeRaw) ? modeRaw : "inner_only";
    const d = parseInt(window.localStorage.getItem(`workspaceGraphDepth:${id}`) || "1", 10);
    const depth = d === 2 ? 2 : 1;
    const includeExternal = window.localStorage.getItem(`workspaceGraphIncludeExternal:${id}`) === "1";
    const nodeTypesCsv = window.localStorage.getItem(`workspaceGraphNodeTypes:${id}`) || "Work,Author";
    return { mode, depth, includeExternal, nodeTypesCsv, externalMinInternalCiters: includeExternal ? 2 : 0 };
  } catch {
    return fallback;
  }
}

export function useGraphWorkspaceData(workspaceId, workId, options = {}) {
  const wsId = String(workspaceId || "").trim();
  const workIdNorm = String(workId || "").trim();
  const [graph, setGraph] = useState(() => normalizeGraphPayload(null));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [wsGraphOpts, setWsGraphOpts] = useState(() => readWsGraphOptsFromLs(wsId));
  const [wsGraphStats, setWsGraphStats] = useState(null);
  const [workspaceGraphRaw, setWorkspaceGraphRaw] = useState(null);
  const [expandNeighborsBusy, setExpandNeighborsBusy] = useState(false);
  const [neighborCache, setNeighborCache] = useState(() => new Set());

  useEffect(() => {
    setWsGraphOpts(readWsGraphOptsFromLs(wsId));
    setWorkspaceGraphRaw(null);
    setNeighborCache(new Set());
  }, [wsId]);

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
          });
          if (cancelled) return;
          setWorkspaceGraphRaw(raw);
          normalized = normalizeGraphPayload(raw);
        } else {
          setNeighborCache(new Set());
          const depth = options.standaloneWorkGraphDepth === 2 ? 2 : 1;
          const raw = await getWorkGraph(w, { depth, view: "reader" });
          if (cancelled) return;
          setWorkspaceGraphRaw(raw.data);
          normalized = normalizeGraphPayload(raw.data);
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
        setWorkspaceGraphRaw(merged);
        setGraph(normalizeGraphPayload(merged));
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
      setExpandNeighborsBusy(true);
      try {
        const extra = await expandAggregator(endpoint);
        const merged = mergeWorkspaceRawGraph(workspaceGraphRaw, extra.data || {});
        setWorkspaceGraphRaw(merged);
        setGraph(normalizeGraphPayload(merged));
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
