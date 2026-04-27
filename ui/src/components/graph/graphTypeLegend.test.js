import React from "react";
import { renderToString } from "react-dom/server";
import { ThemeProvider } from "@mui/material/styles";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "../../i18n/I18nContext.jsx";
import { buildAppTheme } from "../../theme/buildAppTheme.js";
import GraphTypeLegend from "./GraphTypeLegend.jsx";
import {
  collectGraphComposition,
  collectGraphTypeLegend,
  collectGraphTypeLegendByKind,
  sortLegendKinds,
} from "./graphTypeLegend.js";

describe("collectGraphTypeLegend", () => {
  it("returns sorted unique types with defaults", () => {
    const { nodeTypes, edgeTypes } = collectGraphTypeLegend({
      nodes: [{ type: "Work" }, { type: "Author" }, { type: "Work" }],
      edges: [{ type: "cites" }, { type: "mentions" }, { type: "cites" }],
    });
    expect(nodeTypes).toEqual(["Author", "Work"]);
    expect(edgeTypes).toEqual(["cites", "mentions"]);
  });

  it("prefers nodeKind over type for node key", () => {
    const { nodeTypes } = collectGraphTypeLegend({
      nodes: [{ type: "Work", nodeKind: "WorkInternal" }, { type: "Work", nodeKind: "WorkExternal" }],
      edges: [],
    });
    expect(nodeTypes).toEqual(["WorkExternal", "WorkInternal"]);
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

describe("collectGraphComposition", () => {
  it("counts nodes by legend kind key and edges by type", () => {
    const c = collectGraphComposition({
      nodes: [
        { nodeKind: "Author" },
        { nodeKind: "Author" },
        { type: "Work" },
      ],
      edges: [{ type: "CITES" }, { type: "CITES" }, { type: "MENTIONS" }],
    });
    expect(c.totalNodes).toBe(3);
    expect(c.totalEdges).toBe(3);
    expect(c.nodeKindCounts.get("Author")).toBe(2);
    expect(c.nodeKindCounts.get("Work")).toBe(1);
    expect(c.edgeTypeCounts.get("CITES")).toBe(2);
    expect(c.edgeTypeCounts.get("MENTIONS")).toBe(1);
  });
});

describe("sortLegendKinds", () => {
  it("sorts by frequency descending then alphabetically", () => {
    const counts = new Map([
      ["A", 1],
      ["B", 5],
      ["C", 5],
    ]);
    expect(sortLegendKinds(["A", "B", "C"], counts, "frequency")).toEqual(["B", "C", "A"]);
  });

  it("sorts alphabetically", () => {
    const counts = new Map([
      ["Z", 99],
      ["A", 1],
    ]);
    expect(sortLegendKinds(["Z", "A"], counts, "alphabet")).toEqual(["A", "Z"]);
  });
});

describe("collectGraphTypeLegendByKind", () => {
  it("groups node kinds into semantic buckets", () => {
    const grouped = collectGraphTypeLegendByKind({
      nodes: [
        { nodeKind: "WorkInternal" },
        { nodeKind: "WorkExternal" },
        { nodeKind: "AuthorshipReification" },
        { nodeKind: "Dataset" },
        { nodeKind: "UnknownKind" },
      ],
    });
    expect(grouped.Work).toEqual(["WorkExternal", "WorkInternal"]);
    expect(grouped.Semantic).toEqual(["Dataset"]);
    expect(grouped.People).toBeUndefined();
    expect(grouped.Other).toEqual(["AuthorshipReification", "UnknownKind"]);
  });
});

describe("GraphTypeLegend SSR smoke", () => {
  it("renders node and edge type labels with counts", () => {
    const theme = buildAppTheme("dark");
    const html = renderToString(
      React.createElement(
        ThemeProvider,
        { theme },
        React.createElement(
          I18nProvider,
          null,
          React.createElement(GraphTypeLegend, {
            graph: {
              nodes: [{ id: "a", type: "Work", nodeKind: "WorkInternal" }],
              edges: [{ source: "a", target: "a", type: "cites" }],
            },
          }),
        ),
      ),
    );
    expect(html).toContain("Work (internal)");
    expect(html).toContain("(1)");
    expect(html).toContain("Nodes");
    expect(html).toContain("cites");
    expect(html).toContain("1 nodes · 1 edges");
  });
});
