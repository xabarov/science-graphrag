import { useCallback, useEffect, useMemo, useState } from "react";

import { CHAT_CONTEXT_SEARCH_DEBOUNCE_MS } from "./chatContextPickerConstants.js";

/**
 * Debounced workspace work search for the article-pick dialog.
 * @param {{ onWorkSearch: (q: string) => Promise<Array<Record<string, unknown>>>, articleOpen: boolean }} args
 */
export function useChatContextArticleSearch({ onWorkSearch, articleOpen }) {
  const [searchInput, setSearchInput] = useState("");
  const [searchOptions, setSearchOptions] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState(false);

  const runSearch = useCallback(
    async (q) => {
      setSearchLoading(true);
      setSearchError(false);
      try {
        const rows = await onWorkSearch(q);
        setSearchOptions(Array.isArray(rows) ? rows : []);
      } catch {
        setSearchOptions([]);
        setSearchError(true);
      } finally {
        setSearchLoading(false);
      }
    },
    [onWorkSearch],
  );

  useEffect(() => {
    if (!articleOpen) return undefined;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSearchInput("");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSearchOptions([]);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSearchError(false);
    return undefined;
  }, [articleOpen]);

  useEffect(() => {
    if (!articleOpen) return undefined;
    let cancelled = false;
    const tid = setTimeout(() => {
      (async () => {
        if (cancelled) return;
        await runSearch(searchInput);
      })();
    }, CHAT_CONTEXT_SEARCH_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(tid);
    };
  }, [articleOpen, searchInput, runSearch]);

  return useMemo(
    () => ({
      searchInput,
      setSearchInput,
      searchOptions,
      searchLoading,
      searchError,
    }),
    [searchInput, searchOptions, searchLoading, searchError],
  );
}
