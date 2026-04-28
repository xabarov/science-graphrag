/** @vitest-environment jsdom */
import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  GRAPH_CANVAS_POINTER_DOWN_EVENT,
  GRAPH_CANVAS_POINTER_UP_EVENT,
} from "../../components/graph/canvas/graphCanvasPointerEvents.js";
import { SHELL_NAVIGATION_INTENT_EVENT } from "../../components/layout/shellNavigationEvents.js";
import { useGraphPhysicsPolicy } from "./useGraphPhysicsPolicy.js";

describe("useGraphPhysicsPolicy", () => {
  it("sets integrationBlocked true on canvas pointer down and false after pointer up tick", async () => {
    vi.useFakeTimers();
    const bus = new EventTarget();
    const animationFrameRef = { current: null };
    const { result } = renderHook(() =>
      useGraphPhysicsPolicy({
        enabled: true,
        simulationSignature: "sig-a",
        animationFrameRef,
        pointerEventTarget: bus,
      }),
    );
    expect(result.current.integrationBlocked).toBe(false);

    act(() => {
      bus.dispatchEvent(new CustomEvent(GRAPH_CANVAS_POINTER_DOWN_EVENT));
    });
    expect(result.current.integrationBlocked).toBe(true);

    act(() => {
      bus.dispatchEvent(new CustomEvent(GRAPH_CANVAS_POINTER_UP_EVENT));
    });
    await act(async () => {
      vi.runAllTimers();
    });
    expect(result.current.integrationBlocked).toBe(false);
    vi.useRealTimers();
  });

  it("cancels a scheduled animation frame id on canvas pointer down", () => {
    const bus = new EventTarget();
    const animationFrameRef = { current: 42 };
    const cancelSpy = vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});

    renderHook(() =>
      useGraphPhysicsPolicy({
        enabled: true,
        simulationSignature: "sig",
        animationFrameRef,
        pointerEventTarget: bus,
      }),
    );

    act(() => {
      bus.dispatchEvent(new CustomEvent(GRAPH_CANVAS_POINTER_DOWN_EVENT));
    });

    expect(cancelSpy).toHaveBeenCalledWith(42);
    expect(animationFrameRef.current).toBe(null);
    cancelSpy.mockRestore();
  });

  it("sets integrationBlocked on shell navigation intent then clears after timeout", async () => {
    vi.useFakeTimers();
    const animationFrameRef = { current: null };
    const { result } = renderHook(() =>
      useGraphPhysicsPolicy({
        enabled: true,
        simulationSignature: "sig",
        animationFrameRef,
        pointerEventTarget: new EventTarget(),
      }),
    );

    act(() => {
      window.dispatchEvent(new CustomEvent(SHELL_NAVIGATION_INTENT_EVENT, { detail: { target: "/x" } }));
    });
    expect(result.current.integrationBlocked).toBe(true);

    await act(async () => {
      vi.advanceTimersByTime(250);
    });
    expect(result.current.integrationBlocked).toBe(false);
    vi.useRealTimers();
  });

  it("clears shell pause when simulationSignature changes", async () => {
    const bus = new EventTarget();
    const animationFrameRef = { current: null };
    const { result, rerender } = renderHook(
      ({ sig }) =>
        useGraphPhysicsPolicy({
          enabled: true,
          simulationSignature: sig,
          animationFrameRef,
          pointerEventTarget: bus,
        }),
      { initialProps: { sig: "sig-1" } },
    );

    act(() => {
      window.dispatchEvent(new CustomEvent(SHELL_NAVIGATION_INTENT_EVENT));
    });
    expect(result.current.integrationBlocked).toBe(true);

    act(() => {
      rerender({ sig: "sig-2" });
    });
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.integrationBlocked).toBe(false);
  });
});
