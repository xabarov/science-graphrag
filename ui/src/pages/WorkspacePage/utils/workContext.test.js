import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildWorkspacePath,
  getLastWorkId,
  getLastWorkspaceTab,
  LAST_WORK_ID_KEY,
  LAST_WORK_TAB_KEY,
  normalizeWorkspaceTab,
  persistWorkId,
  persistWorkspaceTab,
  WORKSPACE_TAB_SLUGS,
} from "./workContext.js";

describe("workContext", () => {
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

  it("supports graph tab in workspace slugs", () => {
    expect(WORKSPACE_TAB_SLUGS).toContain("graph");
    expect(normalizeWorkspaceTab("GRAPH")).toBe("graph");
  });

  it("builds workspace path with tab and work id", () => {
    expect(buildWorkspacePath("w1", "graph")).toBe("/workspace?work_id=w1&tab=graph");
    expect(buildWorkspacePath("", "graph")).toBe("/workspace");
  });

  it("persists and restores last work id", () => {
    persistWorkId("w-123");
    expect(getLastWorkId()).toBe("w-123");
    expect(window.localStorage.getItem(LAST_WORK_ID_KEY)).toBe("w-123");
  });

  it("persists and restores last workspace tab", () => {
    persistWorkspaceTab("graph");
    expect(getLastWorkspaceTab()).toBe("graph");
    expect(window.localStorage.getItem(LAST_WORK_TAB_KEY)).toBe("graph");
  });
});
