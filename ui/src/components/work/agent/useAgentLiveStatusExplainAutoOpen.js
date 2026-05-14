import { useEffect, useRef } from "react";

/**
 * In detailed mode, auto-expand the "how it works" panel once `intent_classified` arrives.
 *
 * @param {{
 *   isSimple: boolean,
 *   isActive: boolean,
 *   showExplainToggle: boolean,
 *   streamEvents: unknown[],
 *   setExplainOpen: import("react").Dispatch<import("react").SetStateAction<boolean>>,
 * }} params
 */
export function useAgentLiveStatusExplainAutoOpen({
  isSimple,
  isActive,
  showExplainToggle,
  streamEvents,
  setExplainOpen,
}) {
  const autoExplainOpenedRef = useRef(false);

  useEffect(() => {
    if (!isActive) autoExplainOpenedRef.current = false;
  }, [isActive]);

  useEffect(() => {
    if (isSimple || !isActive || !showExplainToggle) return;
    if (autoExplainOpenedRef.current) return;
    const evList = Array.isArray(streamEvents) ? streamEvents : [];
    const hasIntent = evList.some(
      (e) => e && typeof e === "object" && String(e.type) === "intent_classified",
    );
    if (!hasIntent) return;
    autoExplainOpenedRef.current = true;
    queueMicrotask(() => {
      setExplainOpen(true);
    });
  }, [isSimple, isActive, showExplainToggle, streamEvents, setExplainOpen]);
}
