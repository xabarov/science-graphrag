/* eslint-disable react-refresh/only-export-components -- Provider + hook share one module */
import React, { createContext, useContext, useMemo } from "react";

const GraphPhysicsPointerBridgeContext = createContext(null);

/**
 * Isolates canvas pointer pause signals from `window` so graph canvas + force sim share one EventTarget.
 * See `useGraphPhysicsPolicy` and `dispatchGraphCanvasPointerDown`.
 *
 * @param {{ children: React.ReactNode }} props
 */
export function GraphPhysicsPointerBridgeProvider({ children }) {
  const pointerBus = useMemo(() => new EventTarget(), []);
  const value = useMemo(() => ({ pointerBus }), [pointerBus]);
  return <GraphPhysicsPointerBridgeContext.Provider value={value}>{children}</GraphPhysicsPointerBridgeContext.Provider>;
}

/** @returns {{ pointerBus: EventTarget } | null} */
export function useGraphPhysicsPointerBridge() {
  return useContext(GraphPhysicsPointerBridgeContext);
}
