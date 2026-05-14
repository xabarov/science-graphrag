/** @vitest-environment jsdom */
import { describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";

import { useAgentLiveStatusExplainAutoOpen } from "./useAgentLiveStatusExplainAutoOpen.js";

describe("useAgentLiveStatusExplainAutoOpen", () => {
  it("does nothing in simple mode", async () => {
    const setExplainOpen = vi.fn();
    renderHook(() =>
      useAgentLiveStatusExplainAutoOpen({
        isSimple: true,
        isActive: true,
        showExplainToggle: true,
        streamEvents: [{ type: "intent_classified" }],
        setExplainOpen,
      }),
    );
    await act(async () => {
      await Promise.resolve();
    });
    expect(setExplainOpen).not.toHaveBeenCalled();
  });

  it("opens explain once intent_classified arrives in detailed active mode", async () => {
    const setExplainOpen = vi.fn();
    const { rerender } = renderHook(
      ({ events }) =>
        useAgentLiveStatusExplainAutoOpen({
          isSimple: false,
          isActive: true,
          showExplainToggle: true,
          streamEvents: events,
          setExplainOpen,
        }),
      { initialProps: { events: [] } },
    );
    rerender({ events: [{ type: "other" }] });
    await act(async () => {
      await Promise.resolve();
    });
    expect(setExplainOpen).not.toHaveBeenCalled();

    rerender({ events: [{ type: "other" }, { type: "intent_classified" }] });
    await waitFor(() => {
      expect(setExplainOpen).toHaveBeenCalledWith(true);
    });
  });

  it("resets auto-open guard when run becomes inactive", async () => {
    const setExplainOpen = vi.fn();
    const { rerender } = renderHook(
      ({ isActive, events }) =>
        useAgentLiveStatusExplainAutoOpen({
          isSimple: false,
          isActive,
          showExplainToggle: true,
          streamEvents: events,
          setExplainOpen,
        }),
      { initialProps: { isActive: true, events: [{ type: "intent_classified" }] } },
    );
    await waitFor(() => expect(setExplainOpen).toHaveBeenCalledTimes(1));

    rerender({ isActive: false, events: [{ type: "intent_classified" }] });
    await act(async () => {
      await Promise.resolve();
    });

    setExplainOpen.mockClear();
    rerender({ isActive: true, events: [{ type: "intent_classified" }] });
    await waitFor(() => {
      expect(setExplainOpen).toHaveBeenCalledWith(true);
    });
  });
});
