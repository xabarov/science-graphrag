import { useCallback, useMemo, useState } from "react";

import { buildCombinedMarkdownFromChunks, isChunkFocused, sortChunksByOrder } from "./readerFormatters.js";

/**
 * UI state and derived lists for Reader chunk list + combined markdown.
 * @param {unknown} chunks — API payload with optional `items`
 * @param {{ focusedFingerprint?: string, focusedSection?: string }} focus
 */
export function useReaderChunksState(chunks, { focusedFingerprint = "", focusedSection = "" } = {}) {
  const [chunksOpen, setChunksOpen] = useState(false);

  const orderedItems = useMemo(() => sortChunksByOrder(chunks?.items), [chunks]);

  const combinedMarkdown = useMemo(() => buildCombinedMarkdownFromChunks(orderedItems), [orderedItems]);

  const isChunkHighlighted = useCallback(
    (chunk) => isChunkFocused(chunk, { focusedFingerprint, focusedSection }),
    [focusedFingerprint, focusedSection],
  );

  return {
    chunksOpen,
    setChunksOpen,
    orderedItems,
    combinedMarkdown,
    isChunkHighlighted,
  };
}
