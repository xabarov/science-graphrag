import { useEffect } from "react";
import { screenToWorld } from "../graphCanvasTransform.js";

const MIN_SCALE = 0.06;
const MAX_SCALE = 8;

/**
 * Wheel zoom on canvas element (reads/writes transform via ref).
 *
 * @param {{
 *   canvasRef: import("react").RefObject<HTMLCanvasElement | null>,
 *   transformRef: import("react").MutableRefObject<{ scale: number, tx: number, ty: number }>,
 *   setTransform: (t: { scale: number, tx: number, ty: number }) => void,
 *   enabled?: boolean,
 * }} p
 */
export function useGraphCanvasWheelZoom({ canvasRef, transformRef, setTransform, enabled = true }) {
  useEffect(() => {
    if (!enabled) return undefined;
    const el = canvasRef.current;
    if (!el) return undefined;
    const onWheel = (event) => {
      event.preventDefault();
      const rect = el.getBoundingClientRect();
      const mx = event.clientX - rect.left;
      const my = event.clientY - rect.top;
      const { scale, tx, ty } = transformRef.current;
      const world = screenToWorld(mx, my, scale, tx, ty);
      const factor = event.deltaY > 0 ? 0.92 : 1.08;
      const newScale = Math.min(Math.max(scale * factor, MIN_SCALE), MAX_SCALE);
      const next = { scale: newScale, tx: mx - world.x * newScale, ty: my - world.y * newScale };
      transformRef.current = next;
      setTransform(next);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refs hold latest transform; `enabled` re-attaches when canvas mounts (e.g. graph went from 0 to N nodes)
  }, [canvasRef, enabled, setTransform, transformRef]);
}
