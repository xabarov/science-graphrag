import { useMemo, useSyncExternalStore } from "react";

import {
  TRACEABILITY_HASH_SELECTION_EVENT,
  readTraceabilityGraphSelectionFromHash,
} from "./traceabilityState.js";

/**
 * @param {() => void} onStoreChange
 * @returns {() => void}
 */
function subscribe(onStoreChange) {
  if (typeof window === "undefined") return () => {};
  const w = window;
  const fn = () => onStoreChange();
  w.addEventListener("hashchange", fn);
  w.addEventListener("popstate", fn);
  w.addEventListener(TRACEABILITY_HASH_SELECTION_EVENT, fn);
  return () => {
    w.removeEventListener("hashchange", fn);
    w.removeEventListener("popstate", fn);
    w.removeEventListener(TRACEABILITY_HASH_SELECTION_EVENT, fn);
  };
}

/**
 * Stable string for useSyncExternalStore (reference equality).
 * @returns {string}
 */
function getSelectionSnapshotString() {
  const { nodeId, edgeId, hashHasQuery } = readTraceabilityGraphSelectionFromHash();
  return `${hashHasQuery ? 1 : 0}\x1e${nodeId}\x1e${edgeId}`;
}

/**
 * Subscribe to hash query `node` / `edge` after replaceState-based updates.
 *
 * @returns {{ nodeId: string, edgeId: string, hashHasQuery: boolean }}
 */
export function useHashTraceabilityGraphSelection() {
  const snap = useSyncExternalStore(subscribe, getSelectionSnapshotString, () => "0\x1e\x1e");
  return useMemo(() => {
    const parts = String(snap).split("\x1e");
    return {
      hashHasQuery: parts[0] === "1",
      nodeId: parts[1] ?? "",
      edgeId: parts[2] ?? "",
    };
  }, [snap]);
}
