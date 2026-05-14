import { useEffect, useState } from "react";

import { listBenchmarkCases } from "../../services/benchmarkApi.js";

/**
 * Loads merge_safe + nightly benchmark case lists for the active family.
 *
 * @param {{
 *   benchmarkFamily: string,
 *   nightlyTierParam: string,
 *   setError: import("react").Dispatch<import("react").SetStateAction<string | null>>,
 * }} params
 */
export function useBenchmarkRunLabCaseLists({ benchmarkFamily, nightlyTierParam, setError }) {
  const [mergeSafeCases, setMergeSafeCases] = useState([]);
  const [nightlyCases, setNightlyCases] = useState([]);
  const [loadingCases, setLoadingCases] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadCases() {
      setLoadingCases(true);
      try {
        const fam = benchmarkFamily === "graph" ? "graph" : benchmarkFamily;
        const [merge, nightly] = await Promise.all([
          listBenchmarkCases({ family: fam, tier: "merge_safe" }),
          listBenchmarkCases({ family: fam, tier: nightlyTierParam }),
        ]);
        if (cancelled) return;
        setMergeSafeCases(merge?.items || []);
        setNightlyCases(nightly?.items || []);
      } catch (e) {
        if (!cancelled) setError(e?.message || "failed_to_load_cases");
      } finally {
        if (!cancelled) setLoadingCases(false);
      }
    }
    loadCases();
    return () => {
      cancelled = true;
    };
  }, [benchmarkFamily, nightlyTierParam, setError]);

  return { mergeSafeCases, nightlyCases, loadingCases };
}
