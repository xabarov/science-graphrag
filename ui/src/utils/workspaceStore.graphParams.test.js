import { describe, expect, it, vi, afterEach } from "vitest";
import axios from "axios";

import { getWorkspaceGraph } from "./workspaceStore.js";

vi.mock("./researchApi.js", () => ({
  formatResearchApiError: (e) => String(e?.message || e),
  getResearchApiBaseUrl: () => "",
}));

afterEach(() => {
  vi.restoreAllMocks();
});

describe("getWorkspaceGraph query params", () => {
  it("passes mode depth include_external node_types and external_min_internal_citers", async () => {
    const spy = vi.spyOn(axios, "get").mockResolvedValue({ data: { nodes: [], edges: [], meta: {} } });
    await getWorkspaceGraph("ws-1", {
      mode: "inner_only",
      depth: 2,
      includeExternal: true,
      nodeTypes: "Work,Author",
      externalMinInternalCiters: 2,
      neighborLimit: 120,
    });
    expect(spy).toHaveBeenCalled();
    const url = spy.mock.calls[0][0];
    expect(url).toContain("/v1/workspaces/");
    expect(url).toContain("mode=inner_only");
    expect(url).toContain("depth=2");
    expect(url).toContain("include_external=true");
    expect(url).toContain("node_types=Work%2CAuthor");
    expect(url).toContain("external_min_internal_citers=2");
    expect(url).toContain("neighbor_limit=120");
  });
});
