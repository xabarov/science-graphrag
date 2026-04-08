import { beforeEach, describe, expect, it, vi } from "vitest";

import { ASK_HISTORY_STORAGE_KEY, getAskHistory, getLastAskEntry, rememberAskHistory } from "./askHistoryState.js";

describe("askHistoryState", () => {
  beforeEach(() => {
    const store = {};
    vi.stubGlobal("window", {
      localStorage: {
        getItem: (key) => (key in store ? store[key] : null),
        setItem: (key, value) => {
          store[key] = String(value);
        },
      },
    });
  });

  it("stores recent ask entries and deduplicates by query plus scope", () => {
    rememberAskHistory({ query: "What is YOLO?", workId: "w1", topK: 5, mode: "scoped" });
    rememberAskHistory({ query: "What is YOLO?", workId: "w1", topK: 7, mode: "scoped" });
    const recent = getAskHistory();
    expect(recent).toHaveLength(1);
    expect(recent[0].topK).toBe(7);
  });

  it("keeps global and scoped variants as separate history entries", () => {
    rememberAskHistory({ query: "benchmarks", workId: "", mode: "global" });
    rememberAskHistory({ query: "benchmarks", workId: "w1", mode: "scoped" });
    const recent = getAskHistory();
    expect(recent).toHaveLength(2);
  });

  it("returns the latest saved entry", () => {
    rememberAskHistory({ query: "first question", workId: "", mode: "global", savedAt: "2026-04-08T10:00:00Z" });
    rememberAskHistory({ query: "second question", workId: "w2", mode: "workspace", savedAt: "2026-04-08T11:00:00Z" });
    expect(getLastAskEntry()).toMatchObject({
      query: "second question",
      workId: "w2",
      mode: "workspace",
    });
    expect(window.localStorage.getItem(ASK_HISTORY_STORAGE_KEY)).toContain("second question");
  });
});
