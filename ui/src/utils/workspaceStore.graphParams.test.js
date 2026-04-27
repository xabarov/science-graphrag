import { describe, expect, it, vi, afterEach } from "vitest";

import { getWorkspaceContradictionDetail, getWorkspaceGraph } from "./workspaceStore.js";
import { apiClient } from "../services/apiClient.js";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("getWorkspaceGraph query params", () => {
  it("passes mode include_external external_min_internal_citers (no depth or caps)", async () => {
    const spy = vi.spyOn(apiClient, "get").mockResolvedValue({ data: { nodes: [], edges: [], meta: {} } });
    await getWorkspaceGraph("ws-1", {
      mode: "inner_only",
      includeExternal: true,
      externalMinInternalCiters: 2,
    });
    expect(spy).toHaveBeenCalled();
    const url = spy.mock.calls[0][0];
    expect(url).toContain("/v1/workspaces/");
    expect(url).toContain("mode=inner_only");
    expect(url).not.toContain("depth=");
    expect(url).toContain("include_external=true");
    expect(url).toContain("external_min_internal_citers=2");
    expect(url).not.toContain("neighbor_limit=");
    expect(url).not.toContain("node_types=");
  });

  it("requests contradiction-detail with work_id_a and work_id_b", async () => {
    const spy = vi.spyOn(apiClient, "get").mockResolvedValue({
      data: { workspace_id: "ws-1", relationship: {}, article_contradiction: null },
    });
    const data = await getWorkspaceContradictionDetail("ws-1", "work-a", "work-b");
    expect(spy).toHaveBeenCalled();
    const url = spy.mock.calls[0][0];
    expect(url).toContain("/v1/workspaces/");
    expect(url).toContain("graph/contradiction-detail");
    expect(url).toContain("work_id_a=");
    expect(url).toContain("work_id_b=");
    expect(data.workspace_id).toBe("ws-1");
  });

  it("supports full workspace graph with include_claims", async () => {
    const spy = vi.spyOn(apiClient, "get").mockResolvedValue({ data: { nodes: [], edges: [], meta: {} } });
    await getWorkspaceGraph("ws-1", {
      mode: "full",
      includeExternal: true,
      includeClaims: true,
    });
    const url = spy.mock.calls[0][0];
    expect(url).toContain("mode=full");
    expect(url).not.toContain("depth=");
    expect(url).toContain("include_external=true");
    expect(url).toContain("include_claims=true");
    expect(url).not.toContain("node_types=");
  });
});
