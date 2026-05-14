import { afterEach, describe, expect, it, vi } from "vitest";

import { GRAPH_FLOW_MIN_VIEW_HEIGHT, LS_GRAPH_FLOW_MINIMAP, readGraphFlowMinimapPreference } from "./graphFlowConstants.js";

describe("graphFlowConstants", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("exports min view height", () => {
    expect(GRAPH_FLOW_MIN_VIEW_HEIGHT).toBe(280);
  });

  it("readGraphFlowMinimapPreference defaults true when unset", () => {
    const getItem = vi.fn(() => null);
    const setItem = vi.fn();
    vi.stubGlobal("window", { localStorage: { getItem, setItem } });
    expect(readGraphFlowMinimapPreference()).toBe(true);
  });

  it("readGraphFlowMinimapPreference reads LS key", () => {
    const getItem = vi.fn((k) => (k === LS_GRAPH_FLOW_MINIMAP ? "0" : null));
    vi.stubGlobal("window", { localStorage: { getItem, setItem: vi.fn() } });
    expect(readGraphFlowMinimapPreference()).toBe(false);
  });
});
