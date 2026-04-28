import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  appendAskSessionTurn,
  appendAskSessionTurnToSession,
  buildAgentHistoryDigest,
  clearAskSessionEntries,
  createAskSession,
  getActiveSessionEntries,
  getAskSessionEntries,
  maybeMigrateStandaloneBundleToWorkspaceScope,
  readAskSessionUi,
  removeAskSession,
  removeAskSessionTurn,
  truncateAskSessionFromTurn,
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

describe("appendAskSessionTurnToSession", () => {
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

  it("appends to a non-active session without switching active", () => {
    const sk = "scope-two-sessions";
    const id1 = createAskSession(sk, "First");
    appendAskSessionTurn(sk, { query: "q1", workId: "", topK: 5 });
    const id2 = createAskSession(sk, "Second");
    appendAskSessionTurn(sk, { query: "q2", workId: "", topK: 5 });
    appendAskSessionTurnToSession(sk, id1, { query: "q3", workId: "", topK: 5 });
    expect(readAskSessionUi(sk).activeId).toBe(id2);
    const entries1 = getAskSessionEntries(sk, id1);
    const entries2 = getAskSessionEntries(sk, id2);
    expect(entries2[0].query).toBe("q2");
    expect(entries1[0].query).toBe("q3");
    expect(entries1.some((e) => e.query === "q1")).toBe(true);
  });
});

describe("clearAskSessionEntries / truncateAskSessionFromTurn / removeAskSession", () => {
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

  it("clearAskSessionEntries empties turns", () => {
    const sk = "scope-clear";
    appendAskSessionTurn(sk, { query: "a", workId: "", topK: 5 });
    const sid = readAskSessionUi(sk).activeId;
    expect(sid).toBeTruthy();
    clearAskSessionEntries(sk, String(sid));
    expect(getAskSessionEntries(sk, String(sid))).toHaveLength(0);
  });

  it("truncateAskSessionFromTurn removes that turn and newer (newest-first)", () => {
    const sk = "scope-trunc";
    const sid = createAskSession(sk, "T");
    appendAskSessionTurn(sk, { id: "turn-old", query: "old", workId: "", topK: 5, savedAt: "2020-01-01T00:00:00.000Z" });
    appendAskSessionTurn(sk, { id: "turn-mid", query: "mid", workId: "", topK: 5, savedAt: "2020-01-02T00:00:00.000Z" });
    appendAskSessionTurn(sk, { id: "turn-new", query: "new", workId: "", topK: 5, savedAt: "2020-01-03T00:00:00.000Z" });
    truncateAskSessionFromTurn(sk, sid, "turn-mid");
    const entries = getAskSessionEntries(sk, sid);
    expect(entries.map((e) => e.query)).toEqual(["old"]);
  });

  it("removeAskSession picks next active when deleting active", () => {
    const sk = "scope-rm";
    const id1 = createAskSession(sk, "A");
    appendAskSessionTurn(sk, { query: "q1", workId: "", topK: 5 });
    const id2 = createAskSession(sk, "B");
    expect(readAskSessionUi(sk).activeId).toBe(id2);
    const { nextActiveId } = removeAskSession(sk, id2);
    expect(nextActiveId).toBe(id1);
    expect(readAskSessionUi(sk).sessions.some((s) => s.id === id2)).toBe(false);
  });

  it("removeAskSessionTurn removes only selected turn", () => {
    const sk = "scope-rm-turn";
    const sid = createAskSession(sk, "Turns");
    appendAskSessionTurn(sk, { id: "turn-1", query: "q1", workId: "", topK: 5 });
    appendAskSessionTurn(sk, { id: "turn-2", query: "q2", workId: "", topK: 5 });
    appendAskSessionTurn(sk, { id: "turn-3", query: "q3", workId: "", topK: 5 });
    removeAskSessionTurn(sk, sid, "turn-2");
    const entries = getAskSessionEntries(sk, sid);
    expect(entries.map((e) => e.id)).toEqual(["turn-3", "turn-1"]);
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
