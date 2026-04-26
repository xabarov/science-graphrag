import { useEffect, useRef, useState } from "react";

import { getBenchmarkCaseArtifacts, getBenchmarkCaseDetail } from "../../../services/benchmarkApi.js";

/**
 * Loads benchmark case detail + artifacts with cancellation on dependency change.
 * @param {object} args
 * @param {boolean} args.open
 * @param {string | null} args.caseId
 * @param {string} args.family
 * @param {boolean} args.usesLayer1Gold
 * @param {() => void} [args.onDetailFetchStart] Called when a new detail fetch begins (e.g. reset tabs).
 */
export function useCaseDetailDialogData({ open, caseId, family, usesLayer1Gold, onDetailFetchStart }) {
  const onDetailFetchStartRef = useRef(onDetailFetchStart);
  onDetailFetchStartRef.current = onDetailFetchStart;

  const [detail, setDetail] = useState(null);
  const [artifacts, setArtifacts] = useState(null);
  const [goldSource, setGoldSource] = useState("curated_gold");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadArtifacts() {
      if (!open || !caseId) {
        setArtifacts(null);
        return;
      }
      try {
        const resp = await getBenchmarkCaseArtifacts(caseId, { family });
        if (!cancelled) setArtifacts(resp);
      } catch {
        if (!cancelled) setArtifacts(null);
      }
    }
    loadArtifacts();
    return () => {
      cancelled = true;
    };
  }, [open, caseId, family]);

  useEffect(() => {
    if (!open || !caseId) return;
    setGoldSource("curated_gold");
  }, [open, caseId, family]);

  useEffect(() => {
    if (!artifacts || !usesLayer1Gold) return;
    const cur = artifacts.gold_variants?.find((g) => g.id === "curated_gold");
    const tea = artifacts.gold_variants?.find((g) => g.id === "teacher_gold");
    if (!cur?.present && tea?.present) {
      setGoldSource("teacher_gold");
    }
  }, [artifacts, usesLayer1Gold]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!open || !caseId) return;
      onDetailFetchStartRef.current?.();
      setDetail(null);
      setError(null);
      setLoading(true);
      try {
        const resp = await getBenchmarkCaseDetail(caseId, {
          family,
          gold_source: usesLayer1Gold ? goldSource : undefined,
        });
        if (cancelled) return;
        setDetail(resp);
      } catch (e) {
        if (!cancelled) setError(e?.message || "failed_to_fetch_case");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [open, caseId, family, goldSource, usesLayer1Gold]);

  return {
    detail,
    artifacts,
    goldSource,
    setGoldSource,
    loading,
    error,
  };
}
