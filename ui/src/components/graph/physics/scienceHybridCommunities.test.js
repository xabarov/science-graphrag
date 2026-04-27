import { describe, expect, it } from "vitest";

import { detectScienceHybridCommunities } from "./scienceHybridCommunities.js";

describe("detectScienceHybridCommunities", () => {
  it("assigns one community id per disconnected node when no semantic edges", () => {
    const nodes = [{ id: "a" }, { id: "b" }];
    const links = [];
    const m = detectScienceHybridCommunities(nodes, links);
    expect(m.get("a")).toBe("sem:a");
    expect(m.get("b")).toBe("sem:b");
  });

  it("merges Work–Author via projected AUTHORED edge", () => {
    const nodes = [{ id: "w1" }, { id: "auth" }];
    const links = [{ source: "w1", target: "auth", type: "AUTHORED" }];
    const m = detectScienceHybridCommunities(nodes, links);
    const root = m.get("w1");
    expect(m.get("auth")).toBe(root);
  });

  it("merges Work–Authorship–Author chains via HAS_AUTHORSHIP and OF_AUTHOR", () => {
    const nodes = [{ id: "w1" }, { id: "ash" }, { id: "auth" }];
    const links = [
      { source: "w1", target: "ash", type: "HAS_AUTHORSHIP" },
      { source: "ash", target: "auth", type: "OF_AUTHOR" },
    ];
    const m = detectScienceHybridCommunities(nodes, links);
    const root = m.get("w1");
    expect(m.get("ash")).toBe(root);
    expect(m.get("auth")).toBe(root);
  });

  it("ignores non-semantic edge types", () => {
    const nodes = [{ id: "a" }, { id: "b" }];
    const links = [{ source: "a", target: "b", type: "CITES" }];
    const m = detectScienceHybridCommunities(nodes, links);
    expect(m.get("a")).toBe("sem:a");
    expect(m.get("b")).toBe("sem:b");
  });

  it("pins internal Work nodes to ws-internal cluster", () => {
    const nodes = [
      { id: "w1", type: "Work", workspaceMembership: "internal" },
      { id: "w2", type: "Work", workspaceMembership: "external" },
    ];
    const links = [];
    const m = detectScienceHybridCommunities(nodes, links);
    expect(m.get("w1")).toBe("ws-internal");
    expect(m.get("w2")).not.toBe("ws-internal");
  });
});
