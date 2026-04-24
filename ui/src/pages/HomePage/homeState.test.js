import { beforeEach, describe, expect, it, vi } from "vitest";

import { getContinueWorkspaceTarget, getHomeStatus, getRecentWorks, RECENT_WORKS_KEY, rememberRecentWork } from "./homeState.js";
import { LAST_WORK_ID_KEY, LAST_WORK_TAB_KEY } from "../WorkspacePage/utils/workContext.js";

describe("homeState", () => {
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

  it("remembers recent works and deduplicates by work id", () => {
    rememberRecentWork({ workId: "w1", title: "Paper A", tab: "reader", visitedAt: "2026-04-07T00:00:00Z" });
    rememberRecentWork({ workId: "w1", title: "Paper A2", tab: "graph", visitedAt: "2026-04-07T01:00:00Z", workspaceId: "ws-1" });
    const recent = getRecentWorks();
    expect(recent).toHaveLength(1);
    expect(recent[0].title).toBe("Paper A2");
    expect(recent[0].tab).toBe("graph");
    expect(recent[0].workspaceId).toBe("ws-1");
  });

  it("builds continue target from last work and workspace on recent entry", () => {
    window.localStorage.setItem(LAST_WORK_ID_KEY, "w1");
    window.localStorage.setItem(LAST_WORK_TAB_KEY, "graph");
    window.localStorage.setItem(
      RECENT_WORKS_KEY,
      JSON.stringify([
        { workId: "w1", title: "Paper A", tab: "graph", visitedAt: "2026-04-07T01:00:00Z", workspaceId: "ws-a" },
      ]),
    );
    expect(getContinueWorkspaceTarget()).toEqual({
      workId: "w1",
      path: "/workspace?work_id=w1&workspace_id=ws-a",
    });
  });

  it("continue target falls back to active workspace when recent lacks workspaceId", () => {
    window.localStorage.setItem(LAST_WORK_ID_KEY, "w1");
    window.localStorage.setItem("science-graphrag:activeWorkspaceId", "ws-fallback");
    window.localStorage.setItem(
      RECENT_WORKS_KEY,
      JSON.stringify([{ workId: "w1", title: "Paper A", tab: "overview", visitedAt: "2026-04-07T01:00:00Z" }]),
    );
    expect(getContinueWorkspaceTarget()).toEqual({
      workId: "w1",
      path: "/workspace?work_id=w1&workspace_id=ws-fallback",
    });
  });

  it("reports local entry status", () => {
    expect(getHomeStatus()).toEqual({
      hasLastWork: false,
      hasRecentWorks: false,
      hasLocalState: false,
    });
    window.localStorage.setItem(LAST_WORK_ID_KEY, "w1");
    expect(getHomeStatus().hasLastWork).toBe(true);
  });
});
