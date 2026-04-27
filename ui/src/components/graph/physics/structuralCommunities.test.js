import { describe, expect, it } from "vitest";

import { detectScienceHybridCommunities } from "./scienceHybridCommunities.js";
import {
  detectCommunitiesForUi,
  filterTopicLinksForLpa,
  LPA_TOPIC_EDGE_TYPES,
} from "./structuralCommunities.js";

describe("filterTopicLinksForLpa", () => {
  it("keeps only thematic edge types", () => {
    const links = [
      { source: "a", target: "b", type: "CITES" },
      { source: "a", target: "c", type: "AUTHORED" },
      { source: "b", target: "d", type: "USES_METHOD" },
    ];
    const f = filterTopicLinksForLpa(links);
    expect(f).toHaveLength(2);
    expect(f).toEqual(
      expect.arrayContaining([
        { source: "a", target: "b" },
        { source: "b", target: "d" },
      ]),
    );
    expect(LPA_TOPIC_EDGE_TYPES.has("CITES")).toBe(true);
  });
});

describe("detectCommunitiesForUi", () => {
  it("matches hybrid ids when there are no topic edges inside the hybrid group", () => {
    const nodes = [{ id: "w1" }, { id: "a1" }];
    const links = [{ source: "w1", target: "a1", type: "AUTHORED" }];
    const hybrid = detectScienceHybridCommunities(nodes, links);
    const ui = detectCommunitiesForUi(nodes, links);
    expect(ui.get("w1")).toBe(hybrid.get("w1"));
    expect(ui.get("a1")).toBe(hybrid.get("a1"));
  });

  it("can split ws-internal bucket when LPA disagreement exceeds ratio", () => {
    const nodes = Array.from({ length: 9 }, (_, i) => ({
      id: `w${i + 1}`,
      type: "Work",
      workspaceMembership: "internal",
    }));
    const links = [];
    for (let i = 1; i <= 5; i += 1) {
      links.push({ source: `w${i}`, target: `w${i + 1}`, type: "CITES" });
    }
    const ui = detectCommunitiesForUi(nodes, links, { lpaSplitRatio: 0.25 });
    const ids = new Set([...ui.values()]);
    expect(ids.size).toBeGreaterThan(1);
    [...ui.values()].forEach((v) => {
      expect(String(v).startsWith("ws-internal")).toBe(true);
    });
  });
});
