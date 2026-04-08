import { beforeEach, describe, expect, it, vi } from "vitest";

import { ASK_HISTORY_STORAGE_KEY, rememberAskHistory } from "./askHistoryState.js";
import {
  ASK_SESSIONS_STORAGE_KEY,
  appendAskSessionTurn,
  createAskSession,
  deriveAskScopeKey,
  getActiveSessionEntries,
  migrateLegacyAskHistoryToSessions,
  readAskSessionUi,
  renameAskSession,
  sessionExistsInScope,
  setActiveAskSession,
} from "./askSessionState.js";

describe("askSessionState", () => {
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

  it("derives standalone vs workspace scope keys", () => {
    expect(deriveAskScopeKey({ locked: false, scopedWorkId: "w1" })).toBe("standalone");
    expect(deriveAskScopeKey({ locked: true, scopedWorkId: "w1" })).toBe("workspace:w1");
  });

  it("imports legacy flat history once per scope", () => {
    rememberAskHistory({ query: "q1", workId: "w1", topK: 5, mode: "scoped" });
    rememberAskHistory({ query: "q2", workId: "w1", topK: 5, mode: "scoped" });
    migrateLegacyAskHistoryToSessions("workspace:w1", (item) => item.workId === "w1");
    const { sessions, activeId } = readAskSessionUi("workspace:w1");
    expect(sessions).toHaveLength(1);
    expect(sessions[0].title).toBe("Imported");
    expect(activeId).toBe(sessions[0].id);
    expect(sessions[0].entries.map((e) => e.query)).toEqual(["q2", "q1"]);
    migrateLegacyAskHistoryToSessions("workspace:w1", () => true);
    expect(readAskSessionUi("workspace:w1").sessions).toHaveLength(1);
  });

  it("appends turns to the active session and dedupes by query scope id", () => {
    createAskSession("standalone", "Alpha");
    appendAskSessionTurn("standalone", { query: "hello", workId: "", topK: 3, mode: "global" });
    appendAskSessionTurn("standalone", { query: "hello", workId: "", topK: 5, mode: "global" });
    const entries = getActiveSessionEntries("standalone");
    expect(entries).toHaveLength(1);
    expect(entries[0].topK).toBe(5);
  });

  it("sessionExistsInScope reflects stored sessions", () => {
    const id = createAskSession("standalone", "Exists");
    expect(sessionExistsInScope("standalone", id)).toBe(true);
    expect(sessionExistsInScope("standalone", "missing")).toBe(false);
  });

  it("supports switching active session and rename", () => {
    const a = createAskSession("standalone", "One");
    const b = createAskSession("standalone", "Two");
    expect(readAskSessionUi("standalone").activeId).toBe(b);
    setActiveAskSession("standalone", a);
    expect(readAskSessionUi("standalone").activeId).toBe(a);
    renameAskSession("standalone", a, "Renamed");
    expect(readAskSessionUi("standalone").sessions.find((s) => s.id === a)?.title).toBe("Renamed");
  });

  it("stores sessions in versioned localStorage key", () => {
    createAskSession("standalone", "X");
    const raw = window.localStorage.getItem(ASK_SESSIONS_STORAGE_KEY);
    expect(raw).toBeTruthy();
    expect(JSON.parse(raw).version).toBe(1);
    rememberAskHistory({ query: "legacy", workId: "", mode: "global" });
    expect(window.localStorage.getItem(ASK_HISTORY_STORAGE_KEY)).toBeTruthy();
  });
});
