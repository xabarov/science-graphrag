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
  resolveSelectedWorkId,
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

  it("builds workspace path with work id (no tab)", () => {
    expect(buildWorkspacePath("w1", "graph")).toBe("/workspace?work_id=w1");
    expect(buildWorkspacePath("", "graph")).toBe("/workspace");
    expect(buildWorkspacePath("w1", "overview", { workspaceId: "ws-1" })).toBe("/workspace?work_id=w1&workspace_id=ws-1");
    expect(buildWorkspacePath("", "overview", { workspaceId: "ws-only" })).toBe("/workspace?workspace_id=ws-only");
  });

  it("resolveSelectedWorkId prefers URL work when it belongs to workspace", () => {
    expect(
      resolveSelectedWorkId({
        workIds: ["gemma-id", "yolo-id"],
        workIdFromUrl: "yolo-id",
      }),
    ).toBe("yolo-id");
  });

  it("resolveSelectedWorkId falls back to first id when URL work is absent or invalid", () => {
    expect(resolveSelectedWorkId({ workIds: ["a", "b"], workIdFromUrl: "" })).toBe("a");
    expect(resolveSelectedWorkId({ workIds: ["a", "b"], workIdFromUrl: "missing" })).toBe("a");
  });

  it("resolveSelectedWorkId uses sole member when one paper", () => {
    expect(resolveSelectedWorkId({ workIds: ["only"], workIdFromUrl: "" })).toBe("only");
    expect(resolveSelectedWorkId({ workIds: ["only"], workIdFromUrl: "other" })).toBe("only");
  });

  it("resolveSelectedWorkId returns empty for empty list", () => {
    expect(resolveSelectedWorkId({ workIds: [], workIdFromUrl: "x" })).toBe("");
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
