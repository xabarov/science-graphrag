import { useEffect, useState } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

/**
 * Returns `true` when the user prefers reduced motion. Updates if the system
 * setting changes during the session. Returns `false` in non-browser /
 * no-`matchMedia` environments (e.g. Vitest happy-dom without overrides).
 *
 * @returns {boolean}
 */
export function useReducedMotionGate() {
  const [reduced, setReduced] = useState(() => {
    try {
      if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
      return Boolean(window.matchMedia(QUERY).matches);
    } catch {
      return false;
    }
  });

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return undefined;
    let mql;
    try {
      mql = window.matchMedia(QUERY);
    } catch {
      return undefined;
    }
    const handler = (event) => setReduced(Boolean(event.matches));
    if (typeof mql.addEventListener === "function") {
      mql.addEventListener("change", handler);
      return () => mql.removeEventListener("change", handler);
    }
    if (typeof mql.addListener === "function") {
      mql.addListener(handler);
      return () => mql.removeListener(handler);
    }
    return undefined;
  }, []);

  return reduced;
}
