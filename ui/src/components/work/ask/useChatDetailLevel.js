import { useCallback, useState } from "react";

import { readChatDetailLevel, writeChatDetailLevel } from "./chatUiPreferences.js";

/**
 * @returns {{ detailLevel: "simple" | "detailed", setDetailLevel: (l: "simple" | "detailed") => void, toggleDetailLevel: () => void }}
 */
export function useChatDetailLevel() {
  const [level, setLevel] = useState(() => readChatDetailLevel());
  const setDetailLevel = useCallback((next) => {
    setLevel(next);
    writeChatDetailLevel(next);
  }, []);
  const toggleDetailLevel = useCallback(() => {
    setLevel((prev) => {
      const next = prev === "simple" ? "detailed" : "simple";
      writeChatDetailLevel(next);
      return next;
    });
  }, []);
  return { detailLevel: level, setDetailLevel, toggleDetailLevel };
}
