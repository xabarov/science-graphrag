import { useCallback, useEffect, useRef, useState } from "react";

import { expandAggregator, formatResearchApiError, getWorkGraph } from "../../../services/researchApi.js";
import { normalizeGraphVisibilityValue } from "../graphVisibilityFilter.js";
import { graphTelemetryEmit } from "../graphTelemetry.js";
import { scheduleDeferredGraphPrefetch } from "../graphWorkspaceDeferred.js";
import { readGraphVisibilityFromLs, writeGraphVisibilityToLs } from "../graphWorkspaceVisibilityLs.js";
import {
  mergeWorkspaceRawGraph,
  prefetchAuthorAggregatorExpansions,
} from "../workspaceGraphMergePrefetch.js";
import {
  getWorkspaceGraph,
  getWorkspaceGraphNeighbors,
  getWorkspaceGraphStats,
} from "../../../utils/workspaceStore.js";
import { normalizeGraphPayload } from "../graphViewState.js";

export { graphVisibilityLocalStorageKey } from "../graphWorkspaceVisibilityLs.js";

export function useGraphWorkspaceData(workspaceId, workId) {
  const wsId = String(workspaceId || "").trim();
  const workIdNorm = String(workId || "").trim();
  const [graph, setGraph] = useState(() => normalizeGraphPayload(null));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [graphVisibility, setGraphVisibilityState] = useState(() => readGraphVisibilityFromLs(wsId, workIdNorm));
  const [wsGraphStats, setWsGraphStats] = useState(null);
  const [workspaceGraphRaw, setWorkspaceGraphRaw] = useState(null);
  const [expandNeighborsBusy, setExpandNeighborsBusy] = useState(false);
  const [neighborCache, setNeighborCache] = useState(() => new Set());
  const authorAggregatorExpandSeenRef = useRef(new Set());

  const setGraphVisibility = useCallback(
    (next) => {
      setGraphVisibilityState((prev) => {
        const patch = typeof next === "function" ? next(prev) : next;
        const merged = normalizeGraphVisibilityValue({ ...prev, ...patch });
        writeGraphVisibilityToLs(wsId, workIdNorm, merged);
        return merged;
      });
    },
    [wsId, workIdNorm],
  );

  useEffect(() => {
    setGraphVisibilityState(readGraphVisibilityFromLs(wsId, workIdNorm));
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
      graphTelemetryEmit("fetchWorkspaceGraphStart", { workspaceId: ws, workId: w });
      try {
        let raw;
        if (ws) {
          raw = await getWorkspaceGraph(ws, {
            mode: "full",
            includeExternal: true,
            externalMinInternalCiters: 0,
            includeClaims: true,
          });
        } else {
          setNeighborCache(new Set());
          const res = await getWorkGraph(w, {
            view: "reader",
            includeClaims: true,
          });
          raw = res.data;
        }
        if (cancelled) return;
        setWorkspaceGraphRaw(raw);
        const normalizedFirst = normalizeGraphPayload(raw);
        setGraph(normalizedFirst);
        if (!cancelled) setLoading(false);
        graphTelemetryEmit("fetchWorkspaceGraphDone", {
          workspaceId: ws,
          workId: w,
          nodes: normalizedFirst.nodeCount,
          edges: normalizedFirst.edgeCount,
        });

        await scheduleDeferredGraphPrefetch();
        if (cancelled) return;
        graphTelemetryEmit("prefetchAggregatorDeferredStart", { workspaceId: ws, workId: w });
        const mergedPrefetched = await prefetchAuthorAggregatorExpansions(raw, authorAggregatorExpandSeenRef.current);
        if (cancelled) return;
        setWorkspaceGraphRaw(mergedPrefetched);
        setGraph(normalizeGraphPayload(mergedPrefetched));
        graphTelemetryEmit("prefetchAggregatorDeferredDone", { workspaceId: ws, workId: w });
      } catch (err) {
        if (cancelled) return;
        setError(formatResearchApiError(err));
        setGraph(normalizeGraphPayload(null));
        setWorkspaceGraphRaw(null);
        graphTelemetryEmit("fetchWorkspaceGraphError", { workspaceId: ws, workId: w });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workIdNorm, workspaceId]);

  const fetchNeighbors = useCallback(
    async (nodeId) => {
      const nid = String(nodeId || "").trim();
      if (!wsId || !nid || !workspaceGraphRaw || neighborCache.has(nid)) return;
      setExpandNeighborsBusy(true);
      graphTelemetryEmit("fetchWorkspaceNeighbors", { workspaceId: wsId, nodeId: nid });
      try {
        const extra = await getWorkspaceGraphNeighbors(wsId, nid);
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
      graphTelemetryEmit("expandAggregator", { endpoint });
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
    graphVisibility,
    setGraphVisibility,
    wsGraphStats,
    expandNeighborsBusy,
    fetchNeighbors,
    expandAggregatorNode,
  };
}
