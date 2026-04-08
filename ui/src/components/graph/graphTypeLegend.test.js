import React from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import GraphTypeLegend from "./GraphTypeLegend.jsx";
import { collectGraphTypeLegend } from "./graphTypeLegend.js";

describe("collectGraphTypeLegend", () => {
  it("returns sorted unique types with defaults", () => {
    const { nodeTypes, edgeTypes } = collectGraphTypeLegend({
      nodes: [{ type: "Work" }, { type: "Author" }, { type: "Work" }],
      edges: [{ type: "cites" }, { type: "mentions" }, { type: "cites" }],
    });
    expect(nodeTypes).toEqual(["Author", "Work"]);
    expect(edgeTypes).toEqual(["cites", "mentions"]);
  });

  it("uses Node and edge fallbacks for missing types", () => {
    const { nodeTypes, edgeTypes } = collectGraphTypeLegend({
      nodes: [{}],
      edges: [{}],
    });
    expect(nodeTypes).toEqual(["Node"]);
    expect(edgeTypes).toEqual(["edge"]);
  });
});

describe("GraphTypeLegend SSR smoke", () => {
  it("renders node and edge type labels", () => {
    const html = renderToString(
      React.createElement(GraphTypeLegend, {
        graph: {
          nodes: [{ id: "a", type: "Work" }],
          edges: [{ source: "a", target: "a", type: "cites" }],
        },
      }),
    );
    expect(html).toContain("Work");
    expect(html).toContain("cites");
    expect(html).toContain("Types in view");
  });
});
