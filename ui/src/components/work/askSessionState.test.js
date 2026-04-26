import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  appendAskSessionTurn,
  buildAgentHistoryDigest,
  getActiveSessionEntries,
  maybeMigrateStandaloneBundleToWorkspaceScope,
} from "./askSessionState.js";

describe("maybeMigrateStandaloneBundleToWorkspaceScope", () => {
  beforeEach(() => {
    const store = {};
    vi.stubGlobal("window", {
      localStorage: {
        getItem: (key) => (key in store ? store[key] : null),
        setItem: (key, value) => {
          store[key] = String(value);
        },
        removeItem: (key) => {
          delete store[key];
        },
        clear: () => {
          Object.keys(store).forEach((k) => {
            delete store[k];
          });
        },
      },
    });
  });

  it("copies standalone turns into standalone-ws when target has no turns", () => {
    appendAskSessionTurn("standalone", { query: "hello", workId: "", topK: 5 });
    maybeMigrateStandaloneBundleToWorkspaceScope("ws-abc");
    const moved = getActiveSessionEntries("standalone-ws:ws-abc");
    expect(moved.length).toBe(1);
    expect(moved[0].query).toBe("hello");
  });

  it("does not overwrite workspace scope that already has turns", () => {
    appendAskSessionTurn("standalone", { query: "from-standalone", workId: "", topK: 5 });
    appendAskSessionTurn("standalone-ws:ws-x", { query: "already-here", workId: "", topK: 5 });
    maybeMigrateStandaloneBundleToWorkspaceScope("ws-x");
    const ws = getActiveSessionEntries("standalone-ws:ws-x");
    expect(ws.some((e) => e.query === "already-here")).toBe(true);
    expect(ws.some((e) => e.query === "from-standalone")).toBe(false);
  });
});

describe("buildAgentHistoryDigest", () => {
  it("returns null for empty input", () => {
    expect(buildAgentHistoryDigest(null)).toBeNull();
    expect(buildAgentHistoryDigest([])).toBeNull();
  });

  it("reverses newest-first input to oldest-first digest and caps at 12 turns", () => {
    /** Same order as session thread: index 0 = newest turn. */
    const entries = Array.from({ length: 15 }, (_, i) => ({
      query: `q${14 - i}`,
      answer: `a${14 - i}`,
    }));
    const dig = buildAgentHistoryDigest(entries);
    expect(dig).toHaveLength(12);
    expect(dig[0].user).toBe("q3");
    expect(dig[0].assistant).toBe("a3");
    expect(dig[11].user).toBe("q14");
  });
});
