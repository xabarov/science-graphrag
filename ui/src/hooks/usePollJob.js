import { useEffect } from "react";

/**
 * Generic polling hook for async backend jobs.
 * Stops when `isTerminal(job)` returns true.
 */
export default function usePollJob({
  enabled,
  intervalMs = 2000,
  fetchJob,
  onUpdate,
  onTerminal,
  onError,
  isTerminal = (job) => job?.status === "completed" || job?.status === "failed",
}) {
  useEffect(() => {
    if (!enabled || typeof fetchJob !== "function") return undefined;
    let cancelled = false;
    let failCount = 0;
    const tick = async () => {
      try {
        const job = await fetchJob();
        if (cancelled) return;
        failCount = 0;
        onUpdate?.(job);
        if (isTerminal(job)) {
          onTerminal?.(job);
        }
      } catch (err) {
        if (cancelled) return;
        failCount += 1;
        onError?.(err, failCount);
      }
    };
    void tick();
    const id = setInterval(() => {
      void tick();
    }, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [enabled, intervalMs, fetchJob, onUpdate, onTerminal, onError, isTerminal]);
}
