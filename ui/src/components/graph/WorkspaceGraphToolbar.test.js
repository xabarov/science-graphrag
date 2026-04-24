import { describe, expect, it } from "vitest";

import { graphToolbarLocalStorageKey } from "./WorkspaceGraphToolbar.jsx";

describe("WorkspaceGraphToolbar storage keys", () => {
  it("matches per-workspace persist contract (Wave J)", () => {
    const wid = "ws-abc";
    expect(graphToolbarLocalStorageKey(wid, "Mode")).toBe("workspaceGraphMode:ws-abc");
    expect(graphToolbarLocalStorageKey(wid, "Depth")).toBe("workspaceGraphDepth:ws-abc");
    expect(graphToolbarLocalStorageKey(wid, "IncludeExternal")).toBe("workspaceGraphIncludeExternal:ws-abc");
    expect(graphToolbarLocalStorageKey(wid, "NodeTypes")).toBe("workspaceGraphNodeTypes:ws-abc");
  });

  it("trims workspace id", () => {
    expect(graphToolbarLocalStorageKey("  x  ", "Mode")).toBe("workspaceGraphMode:x");
  });
});
