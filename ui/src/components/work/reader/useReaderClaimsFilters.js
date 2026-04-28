import { useMemo, useState } from "react";

/**
 * Local filter state + derived options for Reader work claims section.
 * @param {unknown[]} items — claim rows
 */
export function useReaderClaimsFilters(items) {
  const [claimTypeFilter, setClaimTypeFilter] = useState("all");
  const [polarityFilter, setPolarityFilter] = useState("all");

  const claimTypeOptions = useMemo(() => {
    if (!Array.isArray(items)) return [];
    return [...new Set(items.map((x) => String(x.claim_type || "").trim()).filter(Boolean))].sort();
  }, [items]);

  const polarityOptions = useMemo(() => {
    if (!Array.isArray(items)) return [];
    return [...new Set(items.map((x) => String(x.polarity || "").trim()).filter(Boolean))].sort();
  }, [items]);

  const filteredClaims = useMemo(() => {
    if (!Array.isArray(items)) return [];
    return items.filter((cl) => {
      const typeOk = claimTypeFilter === "all" || String(cl.claim_type || "") === claimTypeFilter;
      const polOk = polarityFilter === "all" || String(cl.polarity || "") === polarityFilter;
      return typeOk && polOk;
    });
  }, [items, claimTypeFilter, polarityFilter]);

  return {
    claimTypeFilter,
    setClaimTypeFilter,
    polarityFilter,
    setPolarityFilter,
    claimTypeOptions,
    polarityOptions,
    filteredClaims,
  };
}
