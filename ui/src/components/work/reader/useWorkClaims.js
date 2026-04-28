import { useEffect, useState } from "react";

import { formatResearchApiError, getWorkClaims } from "../../../services/researchApi.js";

/**
 * @typedef {'immediate' | 'deferred'} WorkClaimsFetchPolicy
 */

/**
 * Shared work claims fetch for ReaderClaimsPanel (eager) and ReaderWorkClaimsSection (lazy).
 * @param {string} workId
 * @param {{ enabled: boolean, fetchPolicy: WorkClaimsFetchPolicy, shouldFetch?: boolean }} options
 *   deferred + shouldFetch false: does not clear prior items (matches legacy ReaderWorkBody collapse).
 * @returns {{ items: unknown[], loading: boolean, error: string | null, fetchPhase: 'idle' | 'loading' | 'ready' }}
 */
export function useWorkClaims(workId, { enabled, fetchPolicy, shouldFetch = true }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [fetchPhase, setFetchPhase] = useState(/** @type {'idle' | 'loading' | 'ready'} */ ("idle"));

  const trimmed = workId?.trim() ?? "";
  const baseOk = Boolean(enabled && trimmed);
  const wantFetch = fetchPolicy === "immediate" ? baseOk : baseOk && shouldFetch;

  useEffect(() => {
    if (fetchPolicy === "immediate" && !baseOk) {
      setItems([]);
      setError(null);
      setLoading(false);
      setFetchPhase("idle");
      return undefined;
    }

    if (!wantFetch) {
      return undefined;
    }

    let cancelled = false;
    setFetchPhase("loading");
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getWorkClaims(trimmed);
        if (cancelled) return;
        const raw = res.data?.items;
        setItems(Array.isArray(raw) ? raw : []);
      } catch (err) {
        if (cancelled) return;
        setError(formatResearchApiError(err));
        setItems([]);
      } finally {
        if (!cancelled) {
          setLoading(false);
          setFetchPhase("ready");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [baseOk, enabled, fetchPolicy, trimmed, wantFetch]);

  return { items, loading, error, fetchPhase };
}
