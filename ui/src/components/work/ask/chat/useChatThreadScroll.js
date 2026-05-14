import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import { SCROLL_BOTTOM_THRESHOLD_PX } from "./chatThreadMetrics.js";

/**
 * Scroll container behavior for chat thread: stick-to-bottom, auto-scroll on updates, jump control.
 *
 * @param {{
 *   chronologicalLength: number,
 *   pendingUserQuery: string,
 *   isLoading: boolean,
 *   liveNormalized: unknown,
 *   streamEvents: unknown[],
 *   streamForThisChat: boolean,
 *   openStructuredQuestion: unknown,
 * }} deps
 */
export function useChatThreadScroll({
  chronologicalLength,
  pendingUserQuery,
  isLoading,
  liveNormalized,
  streamEvents,
  streamForThisChat,
  openStructuredQuestion,
}) {
  const containerRef = useRef(null);
  const [stickToBottom, setStickToBottom] = useState(true);
  const stickToBottomRef = useRef(true);

  const updateStickFromScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
    const stick = dist < SCROLL_BOTTOM_THRESHOLD_PX;
    stickToBottomRef.current = stick;
    setStickToBottom(stick);
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;
    el.addEventListener("scroll", updateStickFromScroll, { passive: true });
    return () => el.removeEventListener("scroll", updateStickFromScroll);
  }, [updateStickFromScroll]);

  const scrollContainerToBottom = useCallback((behavior = "auto") => {
    const el = containerRef.current;
    if (!el) return;
    const top = el.scrollHeight - el.clientHeight;
    if (behavior === "smooth") {
      el.scrollTo({ top, behavior: "smooth" });
    } else {
      el.scrollTop = top;
    }
  }, []);

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    if (!stickToBottomRef.current) return;
    scrollContainerToBottom("auto");
  }, [
    scrollContainerToBottom,
    chronologicalLength,
    pendingUserQuery,
    isLoading,
    liveNormalized,
    streamEvents,
    streamForThisChat,
    openStructuredQuestion,
  ]);

  const jumpToBottom = useCallback(() => {
    stickToBottomRef.current = true;
    setStickToBottom(true);
    scrollContainerToBottom("smooth");
  }, [scrollContainerToBottom]);

  return {
    containerRef,
    stickToBottom,
    jumpToBottom,
  };
}
