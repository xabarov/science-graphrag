import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { SHELL_NAVIGATION_INTENT_EVENT } from "../../components/layout/shellNavigationEvents.js";
import {
  GRAPH_CANVAS_POINTER_DOWN_EVENT,
  GRAPH_CANVAS_POINTER_UP_EVENT,
} from "../../components/graph/graphCanvasPointerEvents.js";

const SHELL_NAVIGATION_RESUME_MS = 250;

/**
 * Decides when force-layout physics may run its rAF integrator.
 * - Shell navigation intent briefly pauses integration so HashRouter can commit.
 * - Primary canvas pointer sessions pause integration so hit-tests stay aligned with the finger.
 *
 * @param {object} opts
 * @param {boolean} opts.enabled When false, listeners detach and pause flags clear.
 * @param {string} opts.simulationSignature Clears pause timers when topology/reheat identity changes.
 * @param {React.MutableRefObject<number|null>} opts.animationFrameRef Current rAF handle owned by the integrator; cancelled synchronously on pause triggers.
 * @param {EventTarget} [opts.pointerEventTarget] Target for canvas pointer custom events (defaults to `window`). Use a dedicated `EventTarget` from `GraphPhysicsPointerBridgeProvider` to avoid global coupling.
 * @returns {{ integrationBlocked: boolean }}
 */
export function useGraphPhysicsPolicy({ enabled, simulationSignature, animationFrameRef, pointerEventTarget }) {
  const shellResumeRef = useRef(null);
  const canvasResumeRef = useRef(null);
  const [shellPaused, setShellPaused] = useState(false);
  const [canvasPaused, setCanvasPaused] = useState(false);

  const canvasTarget = useMemo(() => pointerEventTarget ?? (typeof window !== "undefined" ? window : null), [pointerEventTarget]);

  const cancelIntegrationFrame = useCallback(() => {
    const id = animationFrameRef.current;
    if (id != null) {
      cancelAnimationFrame(id);
      animationFrameRef.current = null;
    }
  }, [animationFrameRef]);

  useEffect(() => {
    if (shellResumeRef.current) {
      window.clearTimeout(shellResumeRef.current);
      shellResumeRef.current = null;
    }
    if (canvasResumeRef.current) {
      window.clearTimeout(canvasResumeRef.current);
      canvasResumeRef.current = null;
    }
    // Defer setState: clears in same tick as topology/signature changes would otherwise
    // trip react-hooks/set-state-in-effect (cascading render); microtask is enough for tests/UI.
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setShellPaused(false);
      setCanvasPaused(false);
    });
    return () => {
      cancelled = true;
    };
  }, [enabled, simulationSignature]);

  useEffect(() => {
    if (!enabled) return undefined;
    const onShellIntent = () => {
      cancelIntegrationFrame();
      setShellPaused(true);
      if (shellResumeRef.current) window.clearTimeout(shellResumeRef.current);
      shellResumeRef.current = window.setTimeout(() => {
        shellResumeRef.current = null;
        setShellPaused(false);
      }, SHELL_NAVIGATION_RESUME_MS);
    };
    window.addEventListener(SHELL_NAVIGATION_INTENT_EVENT, onShellIntent);
    return () => {
      if (shellResumeRef.current) {
        window.clearTimeout(shellResumeRef.current);
        shellResumeRef.current = null;
      }
      window.removeEventListener(SHELL_NAVIGATION_INTENT_EVENT, onShellIntent);
    };
  }, [enabled, cancelIntegrationFrame]);

  useEffect(() => {
    if (!enabled || !canvasTarget) return undefined;
    const onCanvasPointerDown = () => {
      if (canvasResumeRef.current) {
        window.clearTimeout(canvasResumeRef.current);
        canvasResumeRef.current = null;
      }
      cancelIntegrationFrame();
      setCanvasPaused(true);
    };
    const onCanvasPointerUp = () => {
      if (canvasResumeRef.current) {
        window.clearTimeout(canvasResumeRef.current);
        canvasResumeRef.current = null;
      }
      canvasResumeRef.current = window.setTimeout(() => {
        canvasResumeRef.current = null;
        setCanvasPaused(false);
      }, 0);
    };
    canvasTarget.addEventListener(GRAPH_CANVAS_POINTER_DOWN_EVENT, onCanvasPointerDown);
    canvasTarget.addEventListener(GRAPH_CANVAS_POINTER_UP_EVENT, onCanvasPointerUp);
    return () => {
      if (canvasResumeRef.current) {
        window.clearTimeout(canvasResumeRef.current);
        canvasResumeRef.current = null;
      }
      canvasTarget.removeEventListener(GRAPH_CANVAS_POINTER_DOWN_EVENT, onCanvasPointerDown);
      canvasTarget.removeEventListener(GRAPH_CANVAS_POINTER_UP_EVENT, onCanvasPointerUp);
    };
  }, [enabled, canvasTarget, cancelIntegrationFrame]);

  const integrationBlocked = shellPaused || canvasPaused;

  return { integrationBlocked };
}
