import { describe, expect, it } from "vitest";

import {
  localizeAggregatorSubtitle,
  localizeAggregatorTitle,
  localizeDirectionHintTooltip,
  localizeEdgeType,
  localizeEdgeTypeKey,
  localizeNodeKind,
  localizeWorkPropertyKey,
} from "./graphLocalize.js";

/** @type {Record<string, string>} */
const MOCK_EN = {
  "graph.detailPanel.direction.lateralHint": "Lateral hint text",
  "graph.workProperty.publication_year": "Publication year",
  "graph.edgeType.CITES": "cites",
  "graph.edgeType.HAS_AUTHORSHIP": "authored by",
  "graph.edgeType.AUTHORED": "wrote",
  "graph.edgeType.EDGE": "edge",
  "graph.edgeType._other": "{{type}}",
  "graph.nodeKind.WorkInternal": "Work (internal)",
  "graph.wsToolbar.nodeType.Author": "Author",
  "graph.aggregator.kind.author_of_work": "{{count}} authors of work",
  "graph.aggregator.kind._other": "{{count}} · {{kind}}",
  "graph.aggregator.subtitleExpand": "Click to expand",
};

function mockT(dict) {
  /** @type {import("./graphLocalize.js").GraphTranslateFn} */
  return (key, vars) => {
    let text = dict[key];
    if (text == null) text = key;
    if (vars && typeof text === "string") {
      for (const [k, v] of Object.entries(vars)) {
        text = text.split(`{{${k}}}`).join(String(v));
      }
    }
    return text;
  };
}

describe("graphLocalize", () => {
  const t = mockT(MOCK_EN);

  it("localizeEdgeType uses raw type only", () => {
    expect(localizeEdgeType({ type: "CITES", displayType: "WRONG" }, t)).toBe("cites");
    expect(localizeEdgeType({ type: "HAS_AUTHORSHIP" }, t)).toBe("authored by");
    expect(localizeEdgeType({ type: "AUTHORED" }, t)).toBe("wrote");
  });

  it("localizeEdgeType falls back for unknown types", () => {
    expect(localizeEdgeType({ type: "CUSTOM_REL" }, t)).toBe("custom rel");
  });

  it("localizeEdgeTypeKey matches localizeEdgeType", () => {
    expect(localizeEdgeTypeKey("CITES", t)).toBe(localizeEdgeType({ type: "CITES" }, t));
  });

  it("localizeNodeKind prefers graph.nodeKind then wsToolbar", () => {
    expect(localizeNodeKind({ nodeKind: "WorkInternal", type: "Work" }, t)).toBe("Work (internal)");
    expect(localizeNodeKind({ nodeKind: "Author", type: "Author" }, t)).toBe("Author");
  });

  it("localizeNodeKind normalizes lowercase API kinds", () => {
    expect(localizeNodeKind({ nodeKind: "workinternal", type: "Work" }, t)).toBe("Work (internal)");
  });

  it("localizeNodeKind returns canonical kind when no dict entry", () => {
    expect(localizeNodeKind({ nodeKind: "UnknownX", type: "UnknownX" }, t)).toBe("UnknownX");
  });

  it("localizeAggregatorTitle uses aggregation_hints", () => {
    const node = {
      nodeKind: "Aggregator",
      raw: {
        aggregation_hints: { aggregator_kind: "author_of_work", count: 8 },
      },
    };
    expect(localizeAggregatorTitle(node, t)).toBe("8 authors of work");
  });

  it("localizeAggregatorTitle falls back to _other", () => {
    const node = {
      raw: { aggregation_hints: { aggregator_kind: "custom_kind_of_work", count: 3 } },
    };
    expect(localizeAggregatorTitle(node, t)).toBe("3 · custom kind of work");
  });

  it("localizeAggregatorSubtitle", () => {
    expect(localizeAggregatorSubtitle(t)).toBe("Click to expand");
  });

  it("localizeWorkPropertyKey uses dictionary then title case", () => {
    expect(localizeWorkPropertyKey("publication_year", t)).toBe("Publication year");
    expect(localizeWorkPropertyKey("unknown_field_xyz", t)).toBe("Unknown Field Xyz");
  });

  it("localizeDirectionHintTooltip returns hint when key exists", () => {
    expect(localizeDirectionHintTooltip("lateral", t)).toBe("Lateral hint text");
    expect(localizeDirectionHintTooltip("outgoing", t)).toBe("");
  });
});
