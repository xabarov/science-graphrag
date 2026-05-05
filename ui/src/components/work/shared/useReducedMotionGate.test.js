/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, renderHook } from "@testing-library/react";

import { useReducedMotionGate } from "./useReducedMotionGate.js";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function mockMatchMedia(matches) {
  const listeners = new Set();
  const mql = {
    matches,
    media: "(prefers-reduced-motion: reduce)",
    onchange: null,
    addEventListener: (_evt, fn) => listeners.add(fn),
    removeEventListener: (_evt, fn) => listeners.delete(fn),
    addListener: (fn) => listeners.add(fn),
    removeListener: (fn) => listeners.delete(fn),
    dispatchEvent: () => true,
  };
  vi.stubGlobal("matchMedia", () => mql);
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: () => mql,
  });
  return {
    fireChange: (next) => {
      mql.matches = next;
      listeners.forEach((fn) => fn({ matches: next }));
    },
  };
}

describe("useReducedMotionGate", () => {
  it("returns false when matchMedia reports no preference", () => {
    mockMatchMedia(false);
    const { result } = renderHook(() => useReducedMotionGate());
    expect(result.current).toBe(false);
  });

  it("returns true when matchMedia indicates reduced motion preference", () => {
    mockMatchMedia(true);
    const { result } = renderHook(() => useReducedMotionGate());
    expect(result.current).toBe(true);
  });

  it("updates when the OS-level setting changes during the session", () => {
    const { fireChange } = mockMatchMedia(false);
    const { result } = renderHook(() => useReducedMotionGate());
    expect(result.current).toBe(false);
    act(() => fireChange(true));
    expect(result.current).toBe(true);
    act(() => fireChange(false));
    expect(result.current).toBe(false);
  });
});
