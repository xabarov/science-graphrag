import { useCallback, useState } from "react";

import { getContinueWorkspaceTarget, getRecentWorks } from "./homeState.js";

/**
 * Shared recent works + continue-workspace target for Home and Corpus entry surfaces.
 * @param {{ recentLimit?: number }} [options]
 */
export function useCorpusEntryState({ recentLimit = 4 } = {}) {
  const [recentWorks, setRecentWorks] = useState(() => getRecentWorks().slice(0, recentLimit));
  const [continueTarget, setContinueTarget] = useState(() => getContinueWorkspaceTarget());

  const refreshCorpusEntryState = useCallback(() => {
    setRecentWorks(getRecentWorks().slice(0, recentLimit));
    setContinueTarget(getContinueWorkspaceTarget());
  }, [recentLimit]);

  return { recentWorks, continueTarget, refreshCorpusEntryState };
}
